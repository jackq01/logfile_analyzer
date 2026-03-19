#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
from datetime import datetime, timedelta

_supabase_client = None
_requests_module = None


def _get_supabase_client():
    global _supabase_client
    if _supabase_client is None:
        from supabase import create_client
        _supabase_client = create_client
    return _supabase_client


def _get_requests():
    global _requests_module
    if _requests_module is None:
        import requests
        _requests_module = requests
    return _requests_module


def get_config_file_path():
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
        base_path = os.path.dirname(base_path)
    return os.path.join(base_path, "config.json")


class AuthManager:
    PRODUCT = "log_analyze"
    _instance = None
    _initialized = False
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config_file=None):
        if AuthManager._initialized:
            return
        AuthManager._initialized = True
        
        if config_file is None:
            config_file = get_config_file_path()
        self.config_file = config_file
        self.SUPABASE_URL = "https://eyntemrzfskruyyoufjq.supabase.co"
        self.SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV5bnRlbXJ6ZnNrcnV5eW91ZmpxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjA3ODM2NzAsImV4cCI6MjA3NjM1OTY3MH0.54dxoX11GDhLMVzLjUC4lOT1f_nh0w7E-aAun9KAtXM"
        
        self.auth_type = "authkey"
        self.authkey = ""
        self.last_check_time = None
        self.last_validation_message = ""
        self.is_valid = False
        
        self.cached_auth_value = None
        self.cached_validation_time = None
        self.cached_result = (False, "")
        
        self._supabase_client_instance = None
        
        self._load_config()
    
    def _load_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.auth_type = config.get("auth_type", "authkey")
                    self.authkey = config.get("authkey", "")
        except Exception as e:
            print(f"加载配置错误: {e}")
            self.auth_type = "authkey"
            self.authkey = ""
    
    def save_config(self, show_message=True):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            else:
                config = {}
            
            config["auth_type"] = self.auth_type
            config["authkey"] = self.authkey
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"保存配置错误: {e}")
            return False
    
    def set_auth_type(self, auth_type):
        if auth_type in ["authkey", "domain"]:
            self.auth_type = auth_type
            self.cached_auth_value = None
            self.cached_validation_time = None
            self.cached_result = (False, "")
            self.save_config()
    
    def get_auth_type(self):
        return self.auth_type
    
    def _get_current_date(self):
        print("正在获取当前日期...")
        requests = _get_requests()
        
        try:
            response = requests.get("https://jsonplaceholder.typicode.com/posts/1", timeout=5)
            if response.status_code == 200:
                date = datetime.now().date()
                return date
        except Exception as e:
            print(f"首选API获取日期失败: {e}")
        
        try:
            response = requests.get("https://httpbin.org/get", timeout=5)
            if response.status_code == 200:
                date = datetime.now().date()
                return date
        except Exception as e:
            print(f"次选API获取日期失败: {e}")
        
        date = datetime.now().date()
        return date
    
    def _init_supabase_client(self):
        if self._supabase_client_instance is not None:
            return self._supabase_client_instance
        
        create_client = _get_supabase_client()
        self._supabase_client_instance = create_client(self.SUPABASE_URL, self.SUPABASE_KEY)
        self._supabase_client_instance.postgrest.session.timeout = 5
        return self._supabase_client_instance
    
    def get_pc_domain(self):
        import socket
        try:
            fqdn = socket.getfqdn()
            if not fqdn or not isinstance(fqdn, str):
                return ''
            fqdn = fqdn.strip()
            if not fqdn:
                return ''
            parts = fqdn.split('.')
            if len(parts) <= 1:
                return fqdn
            domain = '.'.join(parts[1:])
            domain = domain.strip().lower()
            return domain if domain else fqdn
        except Exception:
            return ''
    
    def _get_auth_value(self):
        if self.auth_type == "authkey":
            return self._get_latest_authkey()
        elif self.auth_type == "domain":
            return self.get_pc_domain()
        return ""
    
    def _get_latest_authkey(self):
        """从配置文件获取最新的authkey"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return config.get("authkey", "")
        except Exception as e:
            print(f"读取配置文件错误: {e}")
        return self.authkey
    
    def _query_auth_info(self, supabase_client, auth_value):
        """
        合并查询授权信息，一次查询同时获取授权是否存在和过期日期
        优化说明：将原来的两次数据库查询(_query_auth_exists和_get_expire_date)合并为单次查询，
        减少数据库交互次数，提升查询性能
        返回: (exists, expire_date) 元组
        """
        try:
            response = supabase_client.table("soft_license") \
                .select("id, expire_date") \
                .eq("authkey", auth_value) \
                .eq("product", self.PRODUCT) \
                .execute()
            
            if response.data and len(response.data) > 0:
                record = response.data[0]
                expire_date = None
                if isinstance(record, dict):
                    expire_date_str = record.get("expire_date")
                    if expire_date_str and isinstance(expire_date_str, str):
                        expire_date = datetime.strptime(expire_date_str, "%Y-%m-%d").date()
                return True, expire_date
            return False, None
        except Exception as e:
            print(f"查询授权信息错误: {e}")
            return False, None
    
    def _should_check_date(self):
        if self.last_check_time is None:
            return True
        now = datetime.now()
        if now - self.last_check_time > timedelta(hours=12):
            return True
        return False
    
    def _check_auth_validity(self, expire_date):
        """
        检查授权有效期
        参数: expire_date - 过期日期，由合并查询方法传入，避免重复查询数据库
        """
        if self._should_check_date():
            current_date = self._get_current_date()
            self.last_check_time = datetime.now()
        else:
            current_date = datetime.now().date()
        
        if expire_date is None:
            return False, "无法获取授权有效期信息！"
        
        if current_date > expire_date:
            return False, f"授权已过期，有效期至 {expire_date}！"
        
        days_until_expire = (expire_date - current_date).days
        if days_until_expire <= 3:
            return True, f"授权将在 {days_until_expire} 天后过期，请及时续期！"
        
        return True, f"授权有效，有效期至 {expire_date}"
    
    def validate_auth(self, force_refresh=False):
        auth_value = self._get_auth_value()
        
        if not auth_value:
            if self.auth_type == "authkey":
                self.last_validation_message = "请先在配置中设置authkey！"
            else:
                self.last_validation_message = "无法获取本机域名！"
            self.is_valid = False
            self.cached_result = (False, self.last_validation_message)
            return False, self.last_validation_message
        
        current_time = datetime.now()
        
        if not force_refresh and self.cached_auth_value == auth_value and self.cached_validation_time is not None:
            cache_duration = current_time - self.cached_validation_time
            if cache_duration < timedelta(hours=12):
                self.last_validation_message = self.cached_result[1]
                self.is_valid = self.cached_result[0]
                cached_message = self.cached_result[1]
                return self.is_valid, cached_message
        
        try:
            supabase_client = self._init_supabase_client()
            exists, expire_date = self._query_auth_info(supabase_client, auth_value)
            
            if exists:
                is_valid, message = self._check_auth_validity(expire_date)
                self.last_validation_message = message
                self.is_valid = is_valid
                self.cached_auth_value = auth_value
                self.cached_validation_time = current_time
                self.cached_result = (is_valid, message)
                
                if not is_valid:
                    return False, message
                else:
                    return True, message
            else:
                if self.auth_type == "authkey":
                    self.last_validation_message = "authkey无效，请检查后重试！"
                else:
                    self.last_validation_message = "域名未授权，请联系管理员！"
                self.is_valid = False
                self.cached_auth_value = auth_value
                self.cached_validation_time = current_time
                self.cached_result = (False, self.last_validation_message)
                return False, self.last_validation_message
        except Exception as e:
            self.last_validation_message = "验证授权时发生错误！"
            self.is_valid = False
            self.cached_result = (False, self.last_validation_message)
            return False, self.last_validation_message
    
    def show_error_message(self, parent):
        from ui.message_box import MessageBox
        MessageBox.warning(parent, "认证失败", self.last_validation_message)


_auth_manager_instance = None


def get_auth_manager():
    global _auth_manager_instance
    if _auth_manager_instance is None:
        _auth_manager_instance = AuthManager()
    return _auth_manager_instance


auth_manager = None


def _get_auth_manager_proxy():
    global auth_manager
    if auth_manager is None:
        auth_manager = get_auth_manager()
    return auth_manager
