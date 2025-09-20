#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Visualization Utilities for Issue #284

Provides utility functions for creating dashboard visualizations and charts.
"""

from typing import Any, Dict, List

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def create_asset_type_chart(assets_data: List[Dict[str, Any]]) -> go.Figure:
    """Create asset type distribution pie chart"""
    if not assets_data:
        # Return empty chart
        fig = go.Figure()
        fig.add_annotation(text="No data available", showarrow=False)
        return fig

    # Count asset types
    asset_types: Dict[str, int] = {}
    for asset in assets_data:
        asset_type = asset.get("asset_type", "Unknown")
        asset_types[asset_type] = asset_types.get(asset_type, 0) + 1

    # Create pie chart
    fig = px.pie(
        values=list(asset_types.values()),
        names=list(asset_types.keys()),
        title="Assets by Type",
        color_discrete_map={
            "POSTGRESQL": "#336791",
            "SQLITE": "#003B57",
            "DUCKDB": "#FFC61A",
            "FILE_STORAGE": "#28A745",
        },
    )

    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>",
    )

    fig.update_layout(showlegend=True, height=400, margin=dict(t=50, b=50, l=50, r=50))

    return fig


def create_risk_level_chart(assets_data: List[Dict[str, Any]]) -> go.Figure:
    """Create risk level distribution bar chart"""
    if not assets_data:
        # Return empty chart
        fig = go.Figure()
        fig.add_annotation(text="No data available", showarrow=False)
        return fig

    # Convert risk scores to risk levels
    risk_levels: Dict[str, int] = {}
    for asset in assets_data:
        risk_score = asset.get("risk_score", 0)
        if risk_score >= 20:
            level = "CRITICAL"
        elif risk_score >= 15:
            level = "VERY_HIGH"
        elif risk_score >= 10:
            level = "HIGH"
        elif risk_score >= 5:
            level = "MEDIUM"
        else:
            level = "LOW"

        risk_levels[level] = risk_levels.get(level, 0) + 1

    # Ensure all levels are represented
    all_levels = ["LOW", "MEDIUM", "HIGH", "VERY_HIGH", "CRITICAL"]
    for level in all_levels:
        if level not in risk_levels:
            risk_levels[level] = 0

    # Create bar chart
    fig = px.bar(
        x=all_levels,
        y=[risk_levels[level] for level in all_levels],
        title="Assets by Risk Level",
        color=all_levels,
        color_discrete_map={
            "LOW": "#28A745",
            "MEDIUM": "#FFC107",
            "HIGH": "#FD7E14",
            "VERY_HIGH": "#DC3545",
            "CRITICAL": "#6F1E51",
        },
    )

    fig.update_layout(
        xaxis_title="Risk Level",
        yaxis_title="Number of Assets",
        showlegend=False,
        height=400,
        margin=dict(t=50, b=50, l=50, r=50),
    )

    fig.update_traces(hovertemplate="<b>%{x}</b><br>Count: %{y}<extra></extra>")

    return fig


def create_risk_trend_chart(risk_data: List[Dict[str, Any]]) -> go.Figure:
    """Create risk trend chart with forecasting"""
    if not risk_data:
        # Return empty chart
        fig = go.Figure()
        fig.add_annotation(text="No data available", showarrow=False)
        return fig

    # Convert to DataFrame and sort by date
    df = pd.DataFrame(risk_data)
    df["date"] = pd.to_datetime(df["assessment_date"])
    df = df.sort_values("date")

    # Group by date and calculate daily averages
    daily_risk = df.groupby(df["date"].dt.date).agg({"risk_score": ["mean", "min", "max", "count"]}).reset_index()

    daily_risk.columns = ["date", "avg_risk", "min_risk", "max_risk", "assessment_count"]

    # Create subplot with secondary y-axis
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,
        subplot_titles=("Risk Score Trends", "Assessment Volume"),
        specs=[[{"secondary_y": True}], [{"secondary_y": False}]],
    )

    # Main risk trend line
    fig.add_trace(
        go.Scatter(
            x=daily_risk["date"],
            y=daily_risk["avg_risk"],
            mode="lines+markers",
            name="Average Risk",
            line=dict(color="red", width=3),
            marker=dict(size=6),
            hovertemplate="<b>Date:</b> %{x}<br><b>Avg Risk:</b> %{y:.1f}<extra></extra>",
        ),
        row=1,
        col=1,
    )

    # Risk range band
    fig.add_trace(
        go.Scatter(
            x=daily_risk["date"],
            y=daily_risk["max_risk"],
            mode="lines",
            line=dict(width=0),
            showlegend=False,
            name="Max Risk",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=daily_risk["date"],
            y=daily_risk["min_risk"],
            mode="lines",
            line=dict(width=0),
            fill="tonexty",
            fillcolor="rgba(255,0,0,0.1)",
            name="Risk Range",
            showlegend=True,
            hovertemplate="<b>Date:</b> %{x}<br><b>Min Risk:</b> %{y:.1f}<extra></extra>",
        ),
        row=1,
        col=1,
    )

    # Assessment volume
    fig.add_trace(
        go.Bar(
            x=daily_risk["date"],
            y=daily_risk["assessment_count"],
            name="Daily Assessments",
            marker_color="lightblue",
            hovertemplate="<b>Date:</b> %{x}<br><b>Assessments:</b> %{y}<extra></extra>",
        ),
        row=2,
        col=1,
    )

    # Add risk threshold lines
    fig.add_hline(y=15, line_dash="dash", line_color="orange", annotation_text="High Risk Threshold", row=1)

    fig.add_hline(y=20, line_dash="dash", line_color="red", annotation_text="Critical Risk Threshold", row=1)

    # Update layout
    fig.update_layout(
        title="Risk Score Trends and Assessment Activity",
        height=600,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    fig.update_xaxes(title_text="Date", row=2, col=1)
    fig.update_yaxes(title_text="Risk Score", row=1, col=1)
    fig.update_yaxes(title_text="Assessment Count", row=2, col=1)

    return fig


def create_risk_heatmap(risk_data: List[Dict[str, Any]]) -> go.Figure:
    """Create risk heatmap visualization"""
    if not risk_data:
        # Return empty chart
        fig = go.Figure()
        fig.add_annotation(text="No data available", showarrow=False)
        return fig

    # Create matrix data for heatmap
    # For simplification, we'll create a mock heatmap based on asset names and risk scores
    asset_names = [
        item.get("asset_name", f"Asset {i}") for i, item in enumerate(risk_data[:20])
    ]  # Limit to 20 for visibility
    risk_scores = [item.get("risk_score", 0) for item in risk_data[:20]]

    # Create a simple heatmap matrix
    z_data = []
    for i, score in enumerate(risk_scores):
        z_data.append([score])

    fig = go.Figure(
        data=go.Heatmap(
            z=z_data,
            y=asset_names,
            x=["Risk Score"],
            colorscale="Reds",
            colorbar=dict(title="Risk Score"),
            hovertemplate="<b>Asset:</b> %{y}<br><b>Risk Score:</b> %{z:.1f}<extra></extra>",
        )
    )

    fig.update_layout(
        title="Asset Risk Heatmap",
        height=max(400, len(asset_names) * 25),
        yaxis=dict(title="Assets"),
        xaxis=dict(title=""),
        margin=dict(l=150),
    )

    return fig


def create_compliance_breakdown_chart(compliance_data: List[Dict[str, Any]]) -> go.Figure:
    """Create compliance framework breakdown chart"""
    if not compliance_data:
        # Return empty chart
        fig = go.Figure()
        fig.add_annotation(text="No data available", showarrow=False)
        return fig

    # Extract framework data
    framework_scores: Dict[str, List[float]] = {}
    for item in compliance_data:
        framework = item.get("framework", "Unknown")
        score = item.get("overall_score", 0)

        if framework not in framework_scores:
            framework_scores[framework] = []
        framework_scores[framework].append(score)

    # Calculate averages
    framework_avg = {fw: sum(scores) / len(scores) for fw, scores in framework_scores.items()}

    # Create bar chart
    fig = px.bar(
        x=list(framework_avg.keys()),
        y=list(framework_avg.values()),
        title="Compliance Scores by Framework",
        color=list(framework_avg.values()),
        color_continuous_scale="RdYlGn",
        text=[f"{score:.1f}%" for score in framework_avg.values()],
    )

    fig.update_traces(
        textposition="outside", hovertemplate="<b>Framework:</b> %{x}<br><b>Score:</b> %{y:.1f}%<extra></extra>"
    )

    fig.update_layout(
        xaxis_title="Compliance Framework",
        yaxis_title="Compliance Score (%)",
        yaxis=dict(range=[0, 100]),
        height=400,
        showlegend=False,
    )

    # Add compliance threshold line
    fig.add_hline(y=80, line_dash="dash", line_color="orange", annotation_text="Target Threshold (80%)")

    return fig


def create_compliance_trend_chart(trend_data: List[Dict[str, Any]]) -> go.Figure:
    """Create compliance trend chart"""
    if not trend_data:
        # Return empty chart
        fig = go.Figure()
        fig.add_annotation(text="No data available", showarrow=False)
        return fig

    # Convert to DataFrame
    df = pd.DataFrame(trend_data)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    # Create line chart
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["compliance_score"],
            mode="lines+markers",
            name="Compliance Score",
            line=dict(color="green", width=3),
            marker=dict(size=6),
            hovertemplate="<b>Date:</b> %{x}<br><b>Compliance:</b> %{y:.1f}%<extra></extra>",
        )
    )

    # Add target threshold
    fig.add_hline(y=80, line_dash="dash", line_color="orange", annotation_text="Target (80%)")

    fig.update_layout(
        title="Compliance Score Trend",
        xaxis_title="Date",
        yaxis_title="Compliance Score (%)",
        yaxis=dict(range=[0, 100]),
        height=400,
    )

    return fig


def create_trend_analysis_chart(trends_data: Dict[str, Any]) -> go.Figure:
    """Create trend analysis chart for executive dashboard"""
    if not trends_data:
        # Return empty chart
        fig = go.Figure()
        fig.add_annotation(text="No data available", showarrow=False)
        return fig

    # Extract trend metrics
    metrics = list(trends_data.keys())
    values = list(trends_data.values())

    # Create bar chart with color coding
    colors = ["green" if v > 0 else "red" if v < 0 else "gray" for v in values]

    fig = go.Figure(
        data=[
            go.Bar(
                x=metrics,
                y=values,
                marker_color=colors,
                text=[f"{v:+.1f}" for v in values],
                textposition="outside",
                hovertemplate="<b>Metric:</b> %{x}<br><b>Change:</b> %{y:+.1f}<extra></extra>",
            )
        ]
    )

    fig.update_layout(
        title="Trend Analysis (30-Day Change)",
        xaxis_title="Metrics",
        yaxis_title="Change",
        height=400,
        showlegend=False,
    )

    # Add zero line
    fig.add_hline(y=0, line_dash="dash", line_color="black", line_width=1)

    return fig


def create_performance_chart(performance_data: Dict[str, Any]) -> go.Figure:
    """Create performance metrics chart"""
    if not performance_data:
        # Return empty chart
        fig = go.Figure()
        fig.add_annotation(text="No data available", showarrow=False)
        return fig

    # Extract performance metrics
    metrics = list(performance_data.keys())
    values = list(performance_data.values())

    # Create gauge-style chart using bar chart
    fig = go.Figure()

    for metric, value in zip(metrics, values):
        # Determine color based on value (assuming lower is better for response times)
        if "time" in metric.lower() or "latency" in metric.lower():
            color = "green" if value < 100 else "orange" if value < 200 else "red"
        else:
            color = "blue"

        fig.add_trace(
            go.Bar(
                x=[metric],
                y=[value],
                name=metric,
                marker_color=color,
                text=f"{value}",
                textposition="outside",
                hovertemplate=f"<b>{metric}:</b> {value}<extra></extra>",
            )
        )

    fig.update_layout(
        title="Performance Metrics", xaxis_title="Metrics", yaxis_title="Value", height=400, showlegend=False
    )

    return fig


def create_asset_relationship_graph(assets: List[Dict[str, Any]], relationships: List[Dict[str, Any]]) -> go.Figure:
    """Create asset relationship network graph"""
    if not assets:
        # Return empty chart
        fig = go.Figure()
        fig.add_annotation(text="No asset data available", showarrow=False)
        return fig

    # For simplified implementation, create a mock network visualization
    # In a real implementation, this would use networkx and more complex algorithms

    # Generate node positions
    n_assets = len(assets[:20])  # Limit for visibility
    angles = [2 * np.pi * i / n_assets for i in range(n_assets)]
    radius = 1

    node_x = [radius * np.cos(angle) for angle in angles]
    node_y = [radius * np.sin(angle) for angle in angles]

    # Create edge traces (mock relationships)
    edge_x = []
    edge_y = []

    if relationships:
        for _ in relationships[:10]:  # Limit edges for visibility
            # Find source and target positions
            source_idx = np.random.randint(0, n_assets)
            target_idx = np.random.randint(0, n_assets)

            if source_idx != target_idx:
                edge_x.extend([node_x[source_idx], node_x[target_idx], None])
                edge_y.extend([node_y[source_idx], node_y[target_idx], None])

    # Create edge trace
    edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=2, color="#888"), hoverinfo="none", mode="lines")

    # Create node trace
    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        hoverinfo="text",
        text=[asset.get("name", f"Asset {i}")[:10] for i, asset in enumerate(assets[:n_assets])],
        textposition="middle center",
        marker=dict(
            size=[max(10, min(30, asset.get("risk_score", 10) * 1.5)) for asset in assets[:n_assets]],
            color=[asset.get("risk_score", 10) for asset in assets[:n_assets]],
            colorscale="Reds",
            line=dict(width=2, color="white"),
            opacity=0.8,
            colorbar=dict(title="Risk Score"),
        ),
        hovertext=[
            f"<b>{asset.get('name', f'Asset {i}')}</b><br>"
            f"Type: {asset.get('asset_type', 'Unknown')}<br>"
            f"Risk Score: {asset.get('risk_score', 0)}<br>"
            f"Environment: {asset.get('environment', 'Unknown')}"
            for i, asset in enumerate(assets[:n_assets])
        ],
    )

    # Create figure
    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            title="Asset Relationship Network",
            titlefont_size=16,
            showlegend=False,
            hovermode="closest",
            margin=dict(b=20, l=5, r=5, t=40),
            annotations=[
                dict(
                    text="Node size = Risk Score, Color = Risk Score",
                    showarrow=False,
                    xref="paper",
                    yref="paper",
                    x=0.005,
                    y=-0.002,
                    xanchor="left",
                    yanchor="bottom",
                    font=dict(color="#999", size=12),
                )
            ],
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor="white",
            height=500,
        ),
    )

    return fig
