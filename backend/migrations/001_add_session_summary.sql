-- 对话历史软压缩：为 chat_session 增加 summary 列
-- 用途：缓存较早对话的 LLM 摘要，避免每轮重新摘要（对应 Langchain 记忆课件"摘要式记忆"）
-- 执行方式（根据 DB_TYPE 选其一）：
--   MySQL : mysql -u<user> -p<pass> <db> < migrations/001_add_session_summary.sql
--   SQLite: sqlite3 travel_system.db < migrations/001_add_session_summary.sql

ALTER TABLE chat_session ADD COLUMN summary TEXT NULL COMMENT '较早对话的 LLM 摘要(软压缩缓存)';
