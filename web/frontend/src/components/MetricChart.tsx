import React, { useEffect, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import api from '../services/api';

interface MetricChartProps {
  metricType: string;
  instanceId: string;
  hours?: number;
}

const MetricChart: React.FC<MetricChartProps> = ({ metricType, instanceId, hours = 24 }) => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await api.getMetricHistory(instanceId, metricType, hours);
        const dataPoints = response.data.data_points || [];

        const timestamps = dataPoints.map((dp: any) =>
          new Date(dp.collected_at).toLocaleTimeString()
        );
        const values = dataPoints.map((dp: any) => dp.metric_value);

        setData({
          xAxis: {
            type: 'category',
            data: timestamps,
          },
          yAxis: {
            type: 'value',
          },
          series: [
            {
              data: values,
              type: 'line',
              smooth: true,
              areaStyle: {
                color: 'rgba(59, 130, 246, 0.1)',
              },
              lineStyle: {
                color: '#3b82f6',
                width: 2,
              },
              symbolSize: 4,
            },
          ],
          tooltip: {
            trigger: 'axis',
          },
          grid: {
            left: 50,
            right: 30,
            top: 30,
            bottom: 30,
            containLabel: true,
          },
        });
      } catch (error) {
        console.error('Error fetching metric data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [metricType, instanceId, hours]);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return data ? (
    <ReactECharts
      option={data}
      style={{ height: '300px', width: '100%' }}
      notMerge={true}
      lazyUpdate={true}
    />
  ) : (
    <div className="flex justify-center items-center h-64 text-gray-500">
      No data available
    </div>
  );
};

export default MetricChart;
