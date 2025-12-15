#!/usr/bin/env python3
"""
自动生成斑鸠叫声统计报告

功能：
- 每日报告：当天统计
- 每周报告：本周统计
- 每月报告：本月统计

报告内容包括：
- 总叫声次数
- 最早叫声时间
- 最频繁时段
- 时间分布图
- 趋势分析（周报/月报）

使用方法：
1. 作为 Home Assistant 自动化任务运行
2. 或通过 cron 定时执行
"""

import os
import sys
import sqlite3
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # 无 GUI 环境
import matplotlib.pyplot as plt
from datetime import datetime, date, timedelta
from pathlib import Path
import argparse
from typing import Dict, List, Tuple

# 配置
# 方式1：使用 Home Assistant 数据库（推荐）
HA_DB_PATH = os.getenv('HA_DB_PATH', '/config/home-assistant_v2.db')
# 方式2：使用独立数据库（如果使用 webhook_handler.py）
DB_PATH = os.getenv('DOVE_DB_PATH', '/config/dove_events.db')
REPORTS_DIR = os.getenv('DOVE_REPORTS_DIR', '/config/dove_reports')
LANG = 'zh_CN'  # 中文报告

# 优先使用 Home Assistant 数据库
USE_HA_DB = os.path.exists(HA_DB_PATH) if 'HA_DB_PATH' in os.environ else False

def get_db_connection():
    """获取数据库连接"""
    return sqlite3.connect(DB_PATH)

def load_events(start_date: date, end_date: date) -> pd.DataFrame:
    """加载指定日期范围的事件"""
    if USE_HA_DB:
        # 从 Home Assistant 数据库读取（通过 states 表）
        conn = sqlite3.connect(HA_DB_PATH)
        # Home Assistant 使用 states 表存储实体状态
        # 我们需要从 counter.dove_count_today 的变化中推断事件
        # 或者使用 recorder 的 events 表
        query = """
            SELECT 
                last_updated_ts as timestamp,
                'dove' as species,
                0.8 as confidence
            FROM states
            WHERE entity_id = 'counter.dove_count_today'
            AND DATE(datetime(last_updated_ts / 1000, 'unixepoch', 'localtime')) >= ?
            AND DATE(datetime(last_updated_ts / 1000, 'unixepoch', 'localtime')) < ?
            AND state != LAG(state) OVER (ORDER BY last_updated_ts)
            ORDER BY last_updated_ts
        """
        try:
            df = pd.read_sql_query(query, conn, params=(start_date.isoformat(), end_date.isoformat()))
            conn.close()
            if len(df) > 0:
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                return df
        except Exception as e:
            print(f"从 Home Assistant 数据库读取失败: {e}")
            conn.close()
    
    # 回退到独立数据库
    conn = get_db_connection()
    query = """
        SELECT timestamp, species, confidence
        FROM dove_events
        WHERE DATE(timestamp) >= ? AND DATE(timestamp) < ?
        ORDER BY timestamp
    """
    try:
        df = pd.read_sql_query(query, conn, params=(start_date.isoformat(), end_date.isoformat()))
        conn.close()
        
        if len(df) == 0:
            return pd.DataFrame(columns=['timestamp', 'species', 'confidence'])
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    except Exception as e:
        print(f"从独立数据库读取失败: {e}")
        conn.close()
        return pd.DataFrame(columns=['timestamp', 'species', 'confidence'])

def calculate_daily_stats(df: pd.DataFrame) -> Dict:
    """计算每日统计"""
    if len(df) == 0:
        return {
            'total_calls': 0,
            'first_call_time': None,
            'last_call_time': None,
            'peak_hour': None,
            'peak_count': 0,
            'hourly_distribution': {}
        }
    
    total_calls = len(df)
    first_call_time = df['timestamp'].min()
    last_call_time = df['timestamp'].max()
    
    # 按小时统计
    df['hour'] = df['timestamp'].dt.hour
    hourly_counts = df.groupby('hour').size().to_dict()
    peak_hour = max(hourly_counts.items(), key=lambda x: x[1])[0] if hourly_counts else None
    peak_count = hourly_counts.get(peak_hour, 0) if peak_hour else 0
    
    return {
        'total_calls': total_calls,
        'first_call_time': first_call_time,
        'last_call_time': last_call_time,
        'peak_hour': peak_hour,
        'peak_count': peak_count,
        'hourly_distribution': hourly_counts
    }

def plot_hourly_distribution(hourly_dist: Dict, output_path: str, title: str):
    """绘制小时分布图"""
    hours = list(range(24))
    counts = [hourly_dist.get(h, 0) for h in hours]
    
    plt.figure(figsize=(12, 6))
    plt.bar(hours, counts, color='#4F46E5', alpha=0.7)
    plt.xlabel('小时', fontsize=12)
    plt.ylabel('叫声次数', fontsize=12)
    plt.title(title, fontsize=14, fontweight='bold')
    plt.grid(axis='y', alpha=0.3)
    plt.xticks(hours)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

def generate_daily_report(target_date: date = None) -> str:
    """生成每日报告"""
    if target_date is None:
        target_date = date.today()
    
    start_date = target_date
    end_date = target_date + timedelta(days=1)
    
    df = load_events(start_date, end_date)
    stats = calculate_daily_stats(df)
    
    # 生成报告文本
    report_lines = [
        f"# 斑鸠叫声统计报告 - {target_date.strftime('%Y年%m月%d日')}",
        "",
        "## 概览",
        f"- **总叫声次数**: {stats['total_calls']}",
    ]
    
    if stats['first_call_time']:
        report_lines.extend([
            f"- **最早叫声时间**: {stats['first_call_time'].strftime('%H:%M:%S')}",
            f"- **最晚叫声时间**: {stats['last_call_time'].strftime('%H:%M:%S')}",
        ])
    else:
        report_lines.append("- **今日无斑鸠叫声记录**")
    
    if stats['peak_hour'] is not None:
        report_lines.extend([
            "",
            "## 最活跃时段",
            f"- **最频繁时段**: {stats['peak_hour']:02d}:00 - {stats['peak_hour']+1:02d}:00",
            f"- **该时段次数**: {stats['peak_count']}",
        ])
    
    # 生成图表
    os.makedirs(REPORTS_DIR, exist_ok=True)
    chart_path = os.path.join(REPORTS_DIR, f"daily_{target_date.strftime('%Y%m%d')}.png")
    plot_hourly_distribution(
        stats['hourly_distribution'],
        chart_path,
        f"每日叫声时间分布 - {target_date.strftime('%Y-%m-%d')}"
    )
    
    report_lines.extend([
        "",
        f"![时间分布图]({chart_path})",
    ])
    
    # 保存报告
    report_path = os.path.join(REPORTS_DIR, f"daily_{target_date.strftime('%Y%m%d')}.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    
    print(f"✓ 每日报告已生成: {report_path}")
    return report_path

def generate_weekly_report(target_date: date = None) -> str:
    """生成每周报告"""
    if target_date is None:
        target_date = date.today()
    
    # 计算本周的开始（周一）和结束（周日）
    days_since_monday = target_date.weekday()
    week_start = target_date - timedelta(days=days_since_monday)
    week_end = week_start + timedelta(days=7)
    
    df = load_events(week_start, week_end)
    
    if len(df) == 0:
        report_lines = [
            f"# 斑鸠叫声周报 - {week_start.strftime('%Y-%m-%d')} 至 {week_end.strftime('%Y-%m-%d')}",
            "",
            "本周无斑鸠叫声记录。"
        ]
    else:
        total_calls = len(df)
        daily_counts = df.groupby(df['timestamp'].dt.date).size()
        
        report_lines = [
            f"# 斑鸠叫声周报 - {week_start.strftime('%Y-%m-%d')} 至 {week_end.strftime('%Y-%m-%d')}",
            "",
            "## 本周概览",
            f"- **总叫声次数**: {total_calls}",
            f"- **平均每日**: {total_calls / 7:.1f} 次",
            "",
            "## 每日统计",
            "| 日期 | 次数 |",
            "|------|------|",
        ]
        
        for day, count in daily_counts.items():
            report_lines.append(f"| {day} | {count} |")
        
        # 绘制每日趋势图
        plt.figure(figsize=(10, 5))
        daily_counts.plot(kind='bar', color='#4F46E5', alpha=0.7)
        plt.xlabel('日期', fontsize=12)
        plt.ylabel('叫声次数', fontsize=12)
        plt.title(f'本周每日叫声次数 - {week_start.strftime("%Y-%m-%d")} 至 {week_end.strftime("%Y-%m-%d")}', fontsize=14)
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        chart_path = os.path.join(REPORTS_DIR, f"weekly_{week_start.strftime('%Y%m%d')}.png")
        plt.savefig(chart_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        report_lines.extend([
            "",
            f"![每日趋势图]({chart_path})",
        ])
    
    report_path = os.path.join(REPORTS_DIR, f"weekly_{week_start.strftime('%Y%m%d')}.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    
    print(f"✓ 周报已生成: {report_path}")
    return report_path

def generate_monthly_report(target_date: date = None) -> str:
    """生成每月报告"""
    if target_date is None:
        target_date = date.today()
    
    month_start = date(target_date.year, target_date.month, 1)
    if target_date.month == 12:
        month_end = date(target_date.year + 1, 1, 1)
    else:
        month_end = date(target_date.year, target_date.month + 1, 1)
    
    df = load_events(month_start, month_end)
    
    if len(df) == 0:
        report_lines = [
            f"# 斑鸠叫声月报 - {month_start.strftime('%Y年%m月')}",
            "",
            "本月无斑鸠叫声记录。"
        ]
    else:
        total_calls = len(df)
        daily_counts = df.groupby(df['timestamp'].dt.date).size()
        weekly_counts = df.groupby(df['timestamp'].dt.to_period('W')).size()
        
        report_lines = [
            f"# 斑鸠叫声月报 - {month_start.strftime('%Y年%m月')}",
            "",
            "## 本月概览",
            f"- **总叫声次数**: {total_calls}",
            f"- **平均每日**: {total_calls / len(daily_counts):.1f} 次",
            f"- **平均每周**: {total_calls / len(weekly_counts):.1f} 次",
            "",
            "## 每周统计",
            "| 周次 | 次数 |",
            "|------|------|",
        ]
        
        for week, count in weekly_counts.items():
            report_lines.append(f"| {week} | {count} |")
        
        # 绘制每日趋势图
        plt.figure(figsize=(14, 6))
        daily_counts.plot(kind='line', marker='o', color='#4F46E5', linewidth=2, markersize=4)
        plt.xlabel('日期', fontsize=12)
        plt.ylabel('叫声次数', fontsize=12)
        plt.title(f'本月每日叫声趋势 - {month_start.strftime("%Y年%m月")}', fontsize=14)
        plt.grid(alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        chart_path = os.path.join(REPORTS_DIR, f"monthly_{month_start.strftime('%Y%m')}.png")
        plt.savefig(chart_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        report_lines.extend([
            "",
            f"![每日趋势图]({chart_path})",
        ])
    
    report_path = os.path.join(REPORTS_DIR, f"monthly_{month_start.strftime('%Y%m')}.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    
    print(f"✓ 月报已生成: {report_path}")
    return report_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='生成斑鸠叫声统计报告')
    parser.add_argument('--type', type=str, choices=['daily', 'weekly', 'monthly', 'all'], 
                       default='all', help='报告类型')
    parser.add_argument('--date', type=str, default=None, 
                       help='目标日期 (YYYY-MM-DD)，默认今天')
    parser.add_argument('--db', type=str, default=DB_PATH, help='数据库路径')
    parser.add_argument('--output', type=str, default=REPORTS_DIR, help='报告输出目录')
    
    args = parser.parse_args()
    
    DB_PATH = args.db
    REPORTS_DIR = args.output
    os.makedirs(REPORTS_DIR, exist_ok=True)
    
    target_date = date.today()
    if args.date:
        target_date = datetime.strptime(args.date, '%Y-%m-%d').date()
    
    if args.type in ['daily', 'all']:
        generate_daily_report(target_date)
    
    if args.type in ['weekly', 'all']:
        generate_weekly_report(target_date)
    
    if args.type in ['monthly', 'all']:
        generate_monthly_report(target_date)

