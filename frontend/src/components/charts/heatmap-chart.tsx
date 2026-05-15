"use client";

import ReactECharts from "echarts-for-react";

export function RegionHeatmap({ data }: { data: Record<string, number> }) {
  const regions = Object.keys(data);
  const values = Object.values(data);
  const max = Math.max(...values, 1);

  const option = {
    backgroundColor: "transparent",
    tooltip: { position: "top" },
    grid: { left: 80, right: 20, top: 20, bottom: 40 },
    xAxis: { type: "category", data: regions, axisLabel: { color: "#94A3B8", rotate: 45 } },
    yAxis: { type: "category", data: ["Exposure"], axisLabel: { color: "#94A3B8" } },
    visualMap: {
      min: 0,
      max,
      calculable: true,
      orient: "horizontal",
      left: "center",
      bottom: 0,
      inRange: { color: ["#1E3A5F", "#3B82F6", "#EF4444"] },
      textStyle: { color: "#94A3B8" },
    },
    series: [
      {
        type: "heatmap",
        data: regions.map((r, i) => [i, 0, values[i]]),
        label: { show: true, color: "#F8FAFC" },
        emphasis: { itemStyle: { shadowBlur: 10, shadowColor: "rgba(0,0,0,0.5)" } },
      },
    ],
  };

  return <ReactECharts option={option} style={{ height: 280 }} opts={{ renderer: "canvas" }} />;
}
