/**
 * 碎片宇宙 · 工具函数
 */

/**
 * 将纯数字股票代码转换为后端标准格式（6位.SH/SZ/BJ）
 * 规则：
 *   - 沪市: 600/601/603/605 → .SH
 *   - 深市: 000/001/002/003/300/301 → .SZ
 *   - 北交所: 4xx/8xx → .BJ
 *   - 若已包含后缀则原样返回
 */
export function normalizeStockCode(code: string): string {
  if (!code) return code;

  // 已包含后缀
  if (/^\d{6}\.(SH|SZ|BJ)$/i.test(code)) return code.toUpperCase();

  // 移除可能的空格
  const clean = code.trim();

  // 匹配前缀
  if (/^(600|601|603|605)/.test(clean)) return `${clean}.SH`;
  if (/^(000|001|002|003|300|301)/.test(clean)) return `${clean}.SZ`;
  if (/^(4|8)\d{2}/.test(clean)) return `${clean}.BJ`;

  // 未知前缀，默认 SH
  return `${clean}.SH`;
}

/**
 * 从后端标准格式中提取纯数字代码（"600519.SH" → "600519"）
 */
export function displayStockCode(code: string): string {
  return code?.replace(/\.(SH|SZ|BJ)$/i, "") ?? code;
}
