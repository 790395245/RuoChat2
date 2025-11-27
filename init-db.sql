-- PostgreSQL 初始化脚本
-- 设置时区
SET timezone = 'Asia/Shanghai';

-- 设置字符编码
ALTER DATABASE ruochat2 SET client_encoding TO 'UTF8';
ALTER DATABASE ruochat2 SET default_transaction_isolation TO 'read committed';
ALTER DATABASE ruochat2 SET timezone TO 'Asia/Shanghai';
