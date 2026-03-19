import re
import logging
import datetime
import os
import io
import hashlib
from typing import List, Generator, Optional, Iterable, Callable, Tuple
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from functools import lru_cache
from .utils import LogEntry, parse_log_time

_psutil = None


def _get_psutil():
    global _psutil
    if _psutil is None:
        import psutil
        _psutil = psutil
    return _psutil


_ENCODING_CACHE: dict = {}
_ENCODING_CACHE_MAX_SIZE = 256

def _calculate_dynamic_params(total_size_bytes: int, log_count: int) -> Tuple[int, int]:
    try:
        psutil = _get_psutil()
        mem = psutil.virtual_memory()
        available_mb = mem.available / (1024 * 1024)
        cpu_count = os.cpu_count() or 4
    except Exception:
        available_mb = 4096
        cpu_count = 4
    
    if log_count <= 10000:
        page_size = 1000
        batch_size = 5000
    elif log_count <= 100000:
        page_size = 2000
        batch_size = 10000
    elif log_count <= 1000000:
        page_size = min(5000, max(2000, int(available_mb / 10)))
        batch_size = 20000
    else:
        page_size = min(10000, max(3000, int(available_mb / 5)))
        batch_size = min(50000, max(20000, int(available_mb * 2)))
    
    batch_size = min(batch_size, max(5000, log_count // cpu_count))
    
    logging.info(f"[动态参数] 可用内存: {available_mb:.0f}MB, 日志数: {log_count}, "
                 f"page_size: {page_size}, batch_size: {batch_size}")
    
    return page_size, batch_size

def _detect_encoding_cached(raw_bytes: bytes) -> Tuple[str, bool]:
    """
    带缓存的编码检测
    
    Returns:
        (encoding, success)
    """
    global _ENCODING_CACHE
    
    sample = raw_bytes[:min(4096, len(raw_bytes))]
    cache_key = hashlib.md5(sample).hexdigest()[:16]
    
    if cache_key in _ENCODING_CACHE:
        return _ENCODING_CACHE[cache_key], True
    
    if len(_ENCODING_CACHE) >= _ENCODING_CACHE_MAX_SIZE:
        _ENCODING_CACHE = dict(list(_ENCODING_CACHE.items())[-_ENCODING_CACHE_MAX_SIZE//2:])
    
    encoding = None
    
    try:
        from charset_normalizer import from_bytes
        best = from_bytes(raw_bytes).best()
        if best:
            encoding = best.encoding
    except Exception:
        pass
    
    if not encoding:
        try:
            import chardet
            detected = chardet.detect(raw_bytes)
            encoding = detected.get('encoding')
        except Exception:
            pass
    
    if not encoding:
        encodings = ['utf-8', 'gbk', 'gb2312', 'big5', 'utf-16', 'utf-16le', 'utf-16be', 'latin1']
        for enc in encodings:
            try:
                raw_bytes.decode(enc)
                encoding = enc
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
    
    if encoding:
        _ENCODING_CACHE[cache_key] = encoding
        return encoding, True
    
    return 'utf-8', False

def _sort_key_timestamp(log: LogEntry) -> datetime.datetime:
    return log.timestamp if log.timestamp else datetime.datetime.min

def _process_single_file(args: Tuple) -> Tuple[List[LogEntry], str, bool]:
    """
    处理单个文件的独立函数（用于进程池）
    
    Args:
        args: (file_bytes, file_name, log_pattern_text, time_pattern_text, default_log_pattern, default_time_pattern)
    
    Returns:
        (logs_list, file_name, success)
    """
    file_bytes, file_name, log_pattern_text, time_pattern_text, default_log_pattern, default_time_pattern = args
    
    result_logs = []
    
    try:
        encoding, decode_success = _detect_encoding_cached(file_bytes)
        
        if not decode_success:
            logging.error(f"无法解码文件: {file_name}")
            return [], file_name, False
        
        try:
            content = file_bytes.decode(encoding, errors='replace')
        except Exception:
            content = file_bytes.decode('utf-8', errors='replace')
        
        content = content.replace('\r\n', '\n')
        
        try:
            pattern_text = log_pattern_text.strip() if log_pattern_text and log_pattern_text.strip() else default_log_pattern
            log_pattern = re.compile(pattern_text, re.DOTALL)
        except re.error:
            log_pattern = re.compile(default_log_pattern, re.DOTALL)
        
        try:
            t_pattern_text = time_pattern_text.strip() if time_pattern_text and time_pattern_text.strip() else default_time_pattern
            time_pattern = re.compile(t_pattern_text)
        except re.error:
            time_pattern = re.compile(default_time_pattern)
        
        for match in log_pattern.finditer(content):
            entry = match.group(1).strip()
            if not entry:
                continue
            
            time_match = re.search(time_pattern, entry)
            if time_match:
                time_str = time_match.group(0)
                timestamp = parse_log_time(time_str, t_pattern_text if 't_pattern_text' in dir() else default_time_pattern)
            else:
                time_str = ""
                timestamp = None
            
            log_entry = LogEntry(
                content=entry,
                timestamp=timestamp,
                source_file=file_name,
                time_str=time_str
            )
            result_logs.append(log_entry)
        
        return result_logs, file_name, True
        
    except Exception as e:
        logging.error(f"处理文件 {file_name} 时出错: {e}")
        return [], file_name, False


class LogProcessor:
    def __init__(self, log_regex_pattern, time_regex_pattern, parent=None):
        self.LOG_REGEX_PATTERN = log_regex_pattern
        self.TIME_REGEX_PATTERN = time_regex_pattern
        self.parent = parent
        
        self._log_pattern_cache = {}
        self._time_pattern_cache = {}
        
        self._use_process_pool = True
        self._dynamic_page_size = 1000
        self._dynamic_batch_size = 10000
    
    def _get_cached_log_pattern(self, pattern_text: str) -> re.Pattern:
        if pattern_text not in self._log_pattern_cache:
            if len(self._log_pattern_cache) > 8:
                self._log_pattern_cache.pop(next(iter(self._log_pattern_cache)))
            self._log_pattern_cache[pattern_text] = re.compile(pattern_text, re.DOTALL)
        return self._log_pattern_cache[pattern_text]
    
    def _get_cached_time_pattern(self, pattern_text: str) -> re.Pattern:
        if pattern_text not in self._time_pattern_cache:
            if len(self._time_pattern_cache) > 8:
                self._time_pattern_cache.pop(next(iter(self._time_pattern_cache)))
            self._time_pattern_cache[pattern_text] = re.compile(pattern_text)
        return self._time_pattern_cache[pattern_text]
    
    def get_dynamic_page_size(self) -> int:
        return self._dynamic_page_size
    
    def get_dynamic_batch_size(self) -> int:
        return self._dynamic_batch_size

    def extract_log_info(self, log_entry: str, source_file: str) -> LogEntry:
        time_match = re.search(self.TIME_REGEX_PATTERN, log_entry)
        if time_match:
            time_str = time_match.group(0)
            timestamp = parse_log_time(time_str, self.TIME_REGEX_PATTERN)
            logging.debug(f"[时间戳提取] 日志条目: {log_entry}, 时间戳: {timestamp}")
        else:
            time_str = ""
            timestamp = None
            logging.debug(f"[时间戳提取失败] 日志条目: {log_entry}")
        
        return LogEntry(
            content=log_entry,
            timestamp=timestamp,
            source_file=source_file,
            time_str=time_str
        )

    def parse_log_entries(self, content: str, log_regex_edit, time_regex_edit) -> Generator[str, None, None]:
        content = content.replace('\r\n', '\n')
        
        try:
            log_pattern_text = log_regex_edit.toPlainText().strip() or self.LOG_REGEX_PATTERN
            log_pattern = self._get_cached_log_pattern(log_pattern_text)
        except re.error:
            logging.warning("日志匹配正则表达式无效，使用默认值")
            log_pattern = self._get_cached_log_pattern(self.LOG_REGEX_PATTERN)
        
        try:
            time_pattern_text = time_regex_edit.toPlainText().strip() or self.TIME_REGEX_PATTERN
            time_pattern = self._get_cached_time_pattern(time_pattern_text)
        except re.error:
            logging.warning("时间匹配正则表达式无效，使用默认值")
            time_pattern = self._get_cached_time_pattern(self.TIME_REGEX_PATTERN)
        
        for match in log_pattern.finditer(content):
            entry = match.group(1).strip()
            if entry:
                yield entry

    def process_log_files(self, uploaded_files: List[io.BytesIO], file_names: List[str], 
                          log_regex_edit, time_regex_edit, progress_callback=None) -> Tuple[list, list]:
        total_files = len(uploaded_files)
        
        if total_files == 0:
            return [], []
        
        try:
            log_pattern_text = log_regex_edit.toPlainText().strip() if log_regex_edit else ""
            time_pattern_text = time_regex_edit.toPlainText().strip() if time_regex_edit else ""
        except Exception:
            log_pattern_text = ""
            time_pattern_text = ""
        
        total_size = 0
        file_data_list = []
        for file_obj in uploaded_files:
            file_obj.seek(0)
            data = file_obj.read()
            total_size += len(data)
            file_data_list.append(data)
        
        all_logs = []
        failed_files = []
        
        use_process = self._use_process_pool and total_files > 1
        
        if use_process:
            try:
                process_args = [
                    (file_data, file_name, log_pattern_text, time_pattern_text, 
                     self.LOG_REGEX_PATTERN, self.TIME_REGEX_PATTERN)
                    for file_data, file_name in zip(file_data_list, file_names)
                ]
                
                cpu_count = os.cpu_count() or 4
                max_workers = min(cpu_count, total_files)
                
                with ProcessPoolExecutor(max_workers=max_workers) as executor:
                    futures = {executor.submit(_process_single_file, args): args[1] 
                              for args in process_args}
                    
                    for idx, future in enumerate(as_completed(futures)):
                        file_name = futures[future]
                        try:
                            result_logs, _, success = future.result()
                            if success and result_logs:
                                all_logs.extend(result_logs)
                            else:
                                failed_files.append(file_name)
                        except Exception as e:
                            logging.error(f"处理文件 {file_name} 时发生异常: {e}")
                            failed_files.append(file_name)
                        
                        if progress_callback:
                            progress = int(((idx + 1) / total_files) * 50)
                            progress_callback(progress)
                            
            except Exception as e:
                logging.warning(f"进程池执行失败，回退到线程池: {e}")
                use_process = False
        
        if not use_process:
            def process_file_content(file_data: bytes, file_name: str) -> Tuple[list, str]:
                result_logs = []
                
                encoding, decode_success = _detect_encoding_cached(file_data)
                
                if not decode_success:
                    logging.error(f"无法解码文件: {file_name}")
                    return [], file_name
                
                try:
                    content = file_data.decode(encoding, errors='replace')
                except Exception:
                    content = file_data.decode('utf-8', errors='replace')
                
                content = content.replace('\r\n', '\n')
                
                try:
                    pattern_text = log_pattern_text.strip() if log_pattern_text else self.LOG_REGEX_PATTERN
                    log_pattern = self._get_cached_log_pattern(pattern_text)
                except re.error:
                    log_pattern = self._get_cached_log_pattern(self.LOG_REGEX_PATTERN)
                
                entries = list(log_pattern.finditer(content))
                logging.debug(f"[正则解析] 文件: {file_name}, 解析日志条数: {len(entries)}")
                
                for match in entries:
                    entry = match.group(1).strip()
                    if not entry:
                        continue
                    try:
                        log_info = self.extract_log_info(entry, file_name)
                        result_logs.append(log_info)
                    except Exception as e:
                        logging.error(f"提取日志信息时出错: {e}")
                
                if not result_logs:
                    logging.warning(f"[警告] 文件: {file_name} 未解析出任何日志条目！")
                else:
                    logging.info(f"[完成] 文件: {file_name} 共解析日志条目: {len(result_logs)}")
                
                return result_logs, file_name
            
            with ThreadPoolExecutor(max_workers=min(os.cpu_count() or 1, total_files)) as executor:
                futures = []
                for file_data, file_name in zip(file_data_list, file_names):
                    future = executor.submit(process_file_content, file_data, file_name)
                    futures.append(future)
                
                for idx, future in enumerate(futures):
                    try:
                        result_logs, file_name = future.result()
                        if not result_logs:
                            failed_files.append(file_name)
                        else:
                            all_logs.extend(result_logs)
                    except Exception as e:
                        logging.error(f"处理文件时发生异常: {e}")
                    
                    if progress_callback:
                        progress = int(((idx + 1) / total_files) * 50)
                        progress_callback(progress)
        
        all_logs.sort(key=_sort_key_timestamp)
        
        self._dynamic_page_size, self._dynamic_batch_size = _calculate_dynamic_params(
            total_size, len(all_logs)
        )
        
        if progress_callback:
            progress_callback(60)
        
        return all_logs, failed_files

    def filter_logs_by_time_range(
        self, 
        logs: Iterable[LogEntry], 
        start_time: Optional[datetime.datetime], 
        end_time: Optional[datetime.datetime]
    ) -> List[LogEntry]:
        result = []
        for log in logs:
            timestamp = log.timestamp
            if not timestamp:
                logging.debug(f"[过滤] 无时间戳被过滤: {log.content}")
                continue
            if start_time and timestamp < start_time:
                logging.debug(f"[过滤] 早于开始时间被过滤: {log.content}")
                continue
            if end_time and timestamp > end_time:
                logging.debug(f"[过滤] 晚于结束时间被过滤: {log.content}")
                continue
            result.append(log)
        return result

    def filter_logs_by_keywords(self, logs: Iterable[LogEntry], keywords: List[str]) -> List[LogEntry]:
        if not keywords:
            return list(logs)
        
        valid_keywords = [k.strip() for k in keywords if k.strip()]
        
        if not valid_keywords:
            return list(logs)
        
        has_regex_chars = any(re.search(r'[.*+?^${}()|[\]\\]', k) for k in valid_keywords)
        
        filtered_logs = []
        batch_size = self._dynamic_batch_size
        batch = []
        
        if has_regex_chars:
            try:
                combined_pattern = re.compile("|".join(re.escape(k) for k in valid_keywords), re.IGNORECASE)
                use_combined = True
            except Exception:
                patterns = [re.compile(re.escape(k), re.IGNORECASE) for k in valid_keywords]
                use_combined = False
            
            for log in logs:
                content = log.content
                
                if use_combined:
                    if combined_pattern.search(content):
                        batch.append(log)
                else:
                    if any(p.search(content) for p in patterns):
                        batch.append(log)
                
                if len(batch) >= batch_size:
                    filtered_logs.extend(batch)
                    batch = []
        else:
            lowercase_keywords = [k.lower() for k in valid_keywords]
            
            for log in logs:
                content = log.content.lower()
                
                if any(keyword in content for keyword in lowercase_keywords):
                    batch.append(log)
                
                if len(batch) >= batch_size:
                    filtered_logs.extend(batch)
                    batch = []
        
        filtered_logs.extend(batch)
        return filtered_logs
    
    def clear_caches(self):
        """清除所有缓存"""
        global _ENCODING_CACHE
        self._log_pattern_cache.clear()
        self._time_pattern_cache.clear()
        _ENCODING_CACHE.clear()
        logging.info("[缓存] 已清除所有缓存")
