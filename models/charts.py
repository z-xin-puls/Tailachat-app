# 数据可视化模块（使用pyecharts）
import pandas as pd
import numpy as np
from pyecharts import options as opts
from pyecharts.charts import Line, Bar, Pie, HeatMap, Grid
from pyecharts.globals import ThemeType
from datetime import datetime, timedelta

def create_user_growth_chart(data):
    """创建用户增长趋势图表"""
    if not data:
        return None
    
    # 提取数据
    dates = [item['date'] for item in data]
    counts = [item['count'] for item in data]
    
    # 创建折线图
    line_chart = (
        Line(init_opts=opts.InitOpts(theme=ThemeType.DARK, width="100%", height="450px"))
        .add_xaxis(dates)
        .add_yaxis(
            series_name="活跃用户数",
            y_axis=counts,
            is_smooth=True,
            linestyle_opts=opts.LineStyleOpts(width=3),
            itemstyle_opts=opts.ItemStyleOpts(color="#FF5555"),
            areastyle_opts=opts.AreaStyleOpts(opacity=0.3)
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(title="用户增长趋势", subtitle="每日活跃用户统计"),
            tooltip_opts=opts.TooltipOpts(trigger="axis"),
            xaxis_opts=opts.AxisOpts(type_="category", boundary_gap=False),
            yaxis_opts=opts.AxisOpts(type_="value"),
            legend_opts=opts.LegendOpts(pos_left="right")
        )
    )
    
    return line_chart

def create_room_creation_chart(data):
    """创建房间创建趋势图表"""
    if not data:
        return None
    
    # 提取数据
    dates = [item['date'] for item in data]
    counts = [item['count'] for item in data]
    
    # 创建柱状图
    bar_chart = (
        Bar(init_opts=opts.InitOpts(theme=ThemeType.DARK, width="100%", height="400px"))
        .add_xaxis(dates)
        .add_yaxis(
            series_name="创建房间数",
            y_axis=counts,
            itemstyle_opts=opts.ItemStyleOpts(color="#00FF00")
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(title="房间创建趋势", subtitle="每日创建房间统计"),
            tooltip_opts=opts.TooltipOpts(trigger="axis"),
            xaxis_opts=opts.AxisOpts(type_="category"),
            yaxis_opts=opts.AxisOpts(type_="value"),
            legend_opts=opts.LegendOpts(pos_left="right")
        )
    )
    
    return bar_chart

def create_hourly_activity_chart(data):
    """创建小时级活动分析图表"""
    if not data:
        return None
    
    # 提取数据
    hours = [f"{item['hour']:02d}:00" for item in data]
    counts = [item['count'] for item in data]
    
    # 创建折线图
    line_chart = (
        Line(init_opts=opts.InitOpts(theme=ThemeType.DARK, width="100%", height="450px"))
        .add_xaxis(hours)
        .add_yaxis(
            series_name="活动次数",
            y_axis=counts,
            is_smooth=True,
            linestyle_opts=opts.LineStyleOpts(width=3),
            itemstyle_opts=opts.ItemStyleOpts(color="#FFD700"),
            areastyle_opts=opts.AreaStyleOpts(opacity=0.3)
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(title="24小时活动分析", subtitle="每小时活动统计"),
            tooltip_opts=opts.TooltipOpts(trigger="axis"),
            xaxis_opts=opts.AxisOpts(type_="category", boundary_gap=False),
            yaxis_opts=opts.AxisOpts(type_="value"),
            legend_opts=opts.LegendOpts(pos_left="right")
        )
    )
    
    return line_chart

def create_user_activity_heatmap(data):
    """创建用户活动热力图"""
    if not data:
        return None
    
    # 处理数据为热力图格式
    heatmap_data = []
    for item in data:
        heatmap_data.append([item['weekday'], item['week'], item['count']])
    
    # 创建热力图
    heatmap_chart = (
        HeatMap(init_opts=opts.InitOpts(theme=ThemeType.DARK, width="100%", height="400px"))
        .add_xaxis(["周一", "周二", "周三", "周四", "周五", "周六", "周日"])
        .add_yaxis(
            series_name="活动次数",
            yaxis_data=[f"第{week}周" for week in range(1, 53)],
            value=heatmap_data,
            label_opts=opts.LabelOpts(is_show=False)
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(title="用户活动热力图", subtitle="每周活动分布"),
            tooltip_opts=opts.TooltipOpts(
                trigger="item",
                formatter="{b}: {c}"
            ),
            visualmap_opts=opts.VisualMapOpts(
                min_=0,
                max_=max([item[2] for item in heatmap_data]) if heatmap_data else 1,
                range_text=["高", "低"],
                is_calculable=True,
                orient="horizontal",
                pos_left="center",
                pos_top="top"
            )
        )
    )
    
    return heatmap_chart

def create_user_role_pie_chart(admin_count, user_count):
    """创建用户角色分布饼图"""
    if admin_count == 0 and user_count == 0:
        return None
    
    # 创建饼图
    pie_chart = (
        Pie(init_opts=opts.InitOpts(theme=ThemeType.DARK, width="100%", height="400px"))
        .add(
            series_name="用户角色",
            data_pair=[
                ("管理员", admin_count),
                ("普通用户", user_count)
            ],
            radius=["40%", "70%"],
            label_opts=opts.LabelOpts(formatter="{b}: {c} ({d}%)")
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(title="用户角色分布", subtitle="管理员与普通用户比例"),
            legend_opts=opts.LegendOpts(orient="vertical", pos_top="15%", pos_left="2%")
        )
        .set_series_opts(
            itemstyle_opts={
                "normal": {
                    "color": ["#FF5555", "#00FF00"],
                    "borderColor": "#fff",
                    "borderWidth": 2
                }
            }
        )
    )
    
    return pie_chart

def create_dashboard_grid(user_growth_data, room_creation_data, hourly_activity_data):
    """创建仪表盘独立图表布局"""
    charts = {}
    
    # 用户增长趋势图
    user_chart = create_user_growth_chart(user_growth_data)
    if user_chart:
        charts['user_growth'] = user_chart
    
    # 房间创建趋势图
    room_chart = create_room_creation_chart(room_creation_data)
    if room_chart:
        charts['room_creation'] = room_chart
    
    # 小时级活动分析图
    hourly_chart = create_hourly_activity_chart(hourly_activity_data)
    if hourly_chart:
        charts['hourly_activity'] = hourly_chart
    
    return charts

def create_activity_statistics_chart(stats_data):
    """创建活动统计图表"""
    if not stats_data:
        return None
    
    # 提取数据
    labels = ["总活动次数", "独立用户数", "活跃天数", "日均活动", "每用户活动"]
    values = [
        stats_data.get('total_activities', 0),
        stats_data.get('unique_users', 0),
        stats_data.get('active_days', 0),
        stats_data.get('avg_daily_activities', 0),
        stats_data.get('activities_per_user', 0)
    ]
    
    # 创建柱状图
    bar_chart = (
        Bar(init_opts=opts.InitOpts(theme=ThemeType.DARK, width="100%", height="400px"))
        .add_xaxis(labels)
        .add_yaxis(
            series_name="统计数值",
            y_axis=values,
            itemstyle_opts=opts.ItemStyleOpts(color="#00CED1")
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(title="活动统计概览", subtitle="关键指标展示"),
            tooltip_opts=opts.TooltipOpts(trigger="axis"),
            xaxis_opts=opts.AxisOpts(type_="category"),
            yaxis_opts=opts.AxisOpts(type_="value"),
            legend_opts=opts.LegendOpts(pos_left="right")
        )
    )
    
    return bar_chart
