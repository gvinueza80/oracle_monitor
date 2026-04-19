import React from 'react';

interface MetricCardProps {
  title: string;
  value: number | string;
  unit: string;
  icon: string;
  trend?: 'normal' | 'warning' | 'critical';
  onClick?: () => void;
}

const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  unit,
  icon,
  trend = 'normal',
  onClick,
}) => {
  const getTrendColor = (): string => {
    switch (trend) {
      case 'warning':
        return 'bg-yellow-50 border-yellow-200';
      case 'critical':
        return 'bg-red-50 border-red-200';
      default:
        return 'bg-white border-gray-200';
    }
  };

  const getTrendTextColor = (): string => {
    switch (trend) {
      case 'warning':
        return 'text-yellow-700';
      case 'critical':
        return 'text-red-700';
      default:
        return 'text-gray-700';
    }
  };

  return (
    <div
      onClick={onClick}
      className={`border rounded-lg p-6 cursor-pointer hover:shadow-lg transition-shadow ${getTrendColor()}`}
    >
      <div className="flex justify-between items-start">
        <div>
          <p className={`text-sm font-medium ${getTrendTextColor()}`}>{title}</p>
          <p className="text-3xl font-bold text-gray-900 mt-2">
            {typeof value === 'number' ? value.toFixed(1) : value}
            <span className="text-sm text-gray-600 ml-2">{unit}</span>
          </p>
        </div>
        <div className="text-4xl">{icon}</div>
      </div>
    </div>
  );
};

export default MetricCard;
