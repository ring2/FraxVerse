// 避免和 useAuthStore 的 create 被 rolldown 合并到同一个命名空间
// 如果使用 import { create } 会与 vendor-auth 的 create 冲突
// 改用直接调用 zustand/vanilla 的 createStore 替代
export { createStore as zustandCreate } from "zustand/vanilla";
