import { Spin } from "antd";

const LoadingFallback: React.FC = () => (
  <div
    style={{
      display: "flex",
      justifyContent: "center",
      alignItems: "center",
      height: "400px",
    }}
  >
    <Spin size="large" />
  </div>
);

export default LoadingFallback;
