type Props = {
  title: string;
  value: string | number;
  description?: string;
};

export default function MetricCard({ title, value, description }: Props) {
  return (
    <div className="metric-card">
      <p className="metric-title">{title}</p>
      <p className="metric-value">{value ?? '--'}</p>
      {description && <p className="metric-desc">{description}</p>}
    </div>
  );
}
