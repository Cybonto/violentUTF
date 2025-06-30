import asyncio
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# Load environment variables from .env file
from dotenv import load_dotenv
from plotly.subplots import make_subplots
from scipy import stats
from sklearn.cluster import DBSCAN, KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

# Import utilities
from utils.auth_utils import handle_authentication_and_sidebar
from utils.jwt_manager import jwt_manager
from utils.logging import get_logger

load_dotenv()

logger = get_logger(__name__)

# API Configuration - MUST go through APISIX Gateway
_raw_api_url = os.getenv("VIOLENTUTF_API_URL", "http://localhost:9080")
API_BASE_URL = _raw_api_url.rstrip("/api").rstrip("/")
if not API_BASE_URL:
    API_BASE_URL = "http://localhost:9080"

API_ENDPOINTS = {
    # Authentication endpoints
    "auth_token_info": f"{API_BASE_URL}/api/v1/auth/token/info",
    # Orchestrator endpoints
    "orchestrators": f"{API_BASE_URL}/api/v1/orchestrators",
    "orchestrator_executions": f"{API_BASE_URL}/api/v1/orchestrators/executions",  # List all executions
    "execution_results": f"{API_BASE_URL}/api/v1/orchestrators/executions/{{execution_id}}/results",
    # Analytics endpoints
    "scorer_analytics": f"{API_BASE_URL}/api/v1/scorers/{{scorer_id}}/analytics",
    "generator_analytics": f"{API_BASE_URL}/api/v1/generators/{{generator_id}}/analytics",
    "system_analytics": f"{API_BASE_URL}/api/v1/analytics/system",
}

# --- API Helper Functions ---


def get_auth_headers() -> Dict[str, str]:
    """Get authentication headers for API requests through APISIX Gateway"""
    try:
        # Use jwt_manager for automatic token refresh
        token = jwt_manager.get_valid_token()

        # Fallback token creation if needed
        if not token and st.session_state.get("access_token"):
            token = create_compatible_api_token()

        if not token:
            return {}

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "X-API-Gateway": "APISIX"}

        # Add APISIX API key for AI model access
        apisix_api_key = (
            os.getenv("VIOLENTUTF_API_KEY") or os.getenv("APISIX_API_KEY") or os.getenv("AI_GATEWAY_API_KEY")
        )
        if apisix_api_key:
            headers["apikey"] = apisix_api_key

        return headers
    except Exception as e:
        logger.error(f"Failed to get auth headers: {e}")
        return {}


def api_request(method: str, url: str, **kwargs) -> Optional[Dict[str, Any]]:
    """Make an authenticated API request through APISIX Gateway"""
    headers = get_auth_headers()
    if not headers.get("Authorization"):
        logger.warning("No authentication token available for API request")
        return None

    try:
        logger.debug(f"Making {method} request to {url} through APISIX Gateway")
        response = requests.request(method, url, headers=headers, timeout=30, **kwargs)

        if response.status_code in [200, 201]:
            return response.json()
        else:
            logger.error(f"API Error {response.status_code}: {url} - {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Request exception to {url}: {e}")
        return None


def create_compatible_api_token():
    """Create a FastAPI-compatible token using JWT manager"""
    try:
        from utils.user_context import get_user_context_for_token

        # Get consistent user context regardless of authentication source
        user_context = get_user_context_for_token()
        logger.info(f"Creating API token for consistent user: {user_context['preferred_username']}")

        # Create token with consistent user context
        api_token = jwt_manager.create_token(user_context)

        if api_token:
            logger.info("Successfully created API token using JWT manager")
            st.session_state["api_token"] = api_token
            return api_token
        else:
            st.error("🚨 Security Error: JWT secret key not configured.")
            logger.error("Failed to create API token - JWT secret key not available")
            return None

    except Exception as e:
        st.error(f"❌ Failed to generate API token.")
        logger.error(f"Token creation failed: {e}")
        return None


# --- Data Loading and Processing ---


@st.cache_data(ttl=300)  # 5-minute cache
def load_all_execution_data(days_back: int = 30) -> Dict[str, Any]:
    """Load comprehensive execution data for analysis"""
    try:
        # First get all orchestrators (same approach as Dashboard_2)
        orchestrators_response = api_request("GET", API_ENDPOINTS["orchestrators"])
        if not orchestrators_response:
            return {"executions": [], "results": []}

        # API returns list directly, not wrapped in 'orchestrators' key
        orchestrators = (
            orchestrators_response
            if isinstance(orchestrators_response, list)
            else orchestrators_response.get("orchestrators", [])
        )
        all_executions = []
        all_results = []

        # For each orchestrator, get its executions
        for orchestrator in orchestrators:
            orch_id = orchestrator.get("orchestrator_id")  # Use correct field name
            if not orch_id:
                continue

            # Get executions for this orchestrator
            exec_url = f"{API_BASE_URL}/api/v1/orchestrators/{orch_id}/executions"
            exec_response = api_request("GET", exec_url)

            if exec_response and "executions" in exec_response:
                for execution in exec_response["executions"]:
                    # Add orchestrator info to execution
                    execution["orchestrator_name"] = orchestrator.get("name", "")
                    execution["orchestrator_type"] = orchestrator.get("type", "")
                    all_executions.append(execution)

                    # For now, include all executions and check for results later
                    # TODO: Fix the has_scorer_results flag in the API
                    # if not execution.get('has_scorer_results', False):
                    #     continue

                    # Only try to load results for completed executions
                    execution_id = execution.get("id")
                    execution_status = execution.get("status", "")

                    if not execution_id or execution_status != "completed":
                        continue

                    url = API_ENDPOINTS["execution_results"].format(execution_id=execution_id)
                    details = api_request("GET", url)

                    # Extract scores directly from the response (not nested under 'results')
                    if details and "scores" in details:
                        for score in details["scores"]:
                            try:
                                # Parse metadata
                                metadata = score.get("score_metadata", "{}")
                                if isinstance(metadata, str):
                                    metadata = json.loads(metadata)

                                # Add execution context
                                score["execution_id"] = execution_id
                                score["execution_name"] = execution.get("name")
                                score["execution_time"] = execution.get("created_at")
                                score["metadata"] = metadata

                                all_results.append(score)
                            except Exception as e:
                                logger.error(f"Failed to parse score result: {e}")
                                continue

        return {"executions": all_executions, "results": all_results}

    except Exception as e:
        logger.error(f"Failed to load execution data: {e}")
        return {"executions": [], "results": []}


# --- ML Analysis Functions ---


def prepare_feature_matrix(results: List[Dict[str, Any]]) -> Tuple[pd.DataFrame, np.ndarray]:
    """Prepare feature matrix for ML analysis"""
    features = []

    for result in results:
        metadata = result.get("metadata", {})

        # Extract features with proper score value cleaning
        def clean_score_for_features(x):
            """Clean score value for feature extraction"""
            if x is None or (isinstance(x, float) and np.isnan(x)):
                return 0.0
            if isinstance(x, bool):
                return float(x)
            if isinstance(x, (int, float)):
                return float(x)
            if isinstance(x, str):
                # Handle concatenated strings by taking the first number
                try:
                    import re

                    numbers = re.findall(r"[\d.]+", str(x))
                    if numbers:
                        return float(numbers[0])
                    return 0.0
                except Exception:
                    return 0.0
            return 0.0

        score_val = result.get("score_value")
        score_numeric = clean_score_for_features(score_val)

        feature_dict = {
            # Score features
            "score_value_numeric": score_numeric,
            "is_violation": 1 if result.get("score_value") is True else 0,
            "score_type_boolean": 1 if result.get("score_type") == "true_false" else 0,
            "score_type_scale": 1 if result.get("score_type") == "float_scale" else 0,
            "score_type_category": 1 if result.get("score_type") == "str" else 0,
            # Metadata features
            "batch_index": metadata.get("batch_index", 0),
            "total_batches": metadata.get("total_batches", 1),
            "batch_position": metadata.get("batch_index", 0) / max(metadata.get("total_batches", 1), 1),
            # Temporal features
            "hour": datetime.fromisoformat(
                result.get("execution_time", datetime.now().isoformat()).replace("Z", "+00:00")
            ).hour,
            "day_of_week": datetime.fromisoformat(
                result.get("execution_time", datetime.now().isoformat()).replace("Z", "+00:00")
            ).weekday(),
            # Text features (simplified)
            "rationale_length": len(result.get("score_rationale", "")),
            "has_critical_keywords": (
                1
                if any(
                    kw in result.get("score_rationale", "").lower()
                    for kw in ["critical", "severe", "dangerous", "harmful"]
                )
                else 0
            ),
        }

        features.append(feature_dict)

    df_features = pd.DataFrame(features)

    # Handle missing values
    df_features = df_features.fillna(0)

    # Create feature matrix
    feature_matrix = df_features.values

    return df_features, feature_matrix


def perform_clustering_analysis(feature_matrix: np.ndarray, n_clusters: int = 5) -> Dict[str, Any]:
    """Perform clustering analysis on scorer results"""
    # Standardize features
    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(feature_matrix)

    # PCA for dimensionality reduction
    pca = PCA(n_components=min(3, scaled_features.shape[1]))
    pca_features = pca.fit_transform(scaled_features)

    # K-Means clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    kmeans_labels = kmeans.fit_predict(scaled_features)

    # DBSCAN for anomaly detection
    dbscan = DBSCAN(eps=0.5, min_samples=5)
    dbscan_labels = dbscan.fit_predict(scaled_features)

    # Calculate cluster statistics
    cluster_stats = {}
    for i in range(n_clusters):
        cluster_mask = kmeans_labels == i
        cluster_size = np.sum(cluster_mask)
        cluster_stats[f"cluster_{i}"] = {
            "size": int(cluster_size),
            "percentage": float(cluster_size / len(kmeans_labels) * 100),
        }

    return {
        "pca_features": pca_features,
        "pca_explained_variance": pca.explained_variance_ratio_,
        "kmeans_labels": kmeans_labels,
        "kmeans_centers": kmeans.cluster_centers_,
        "dbscan_labels": dbscan_labels,
        "n_anomalies": int(np.sum(dbscan_labels == -1)),
        "cluster_stats": cluster_stats,
    }


def perform_anomaly_detection(feature_matrix: np.ndarray, contamination: float = 0.1) -> Dict[str, Any]:
    """Perform anomaly detection using Isolation Forest"""
    # Standardize features
    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(feature_matrix)

    # Isolation Forest
    iso_forest = IsolationForest(contamination=contamination, random_state=42)
    anomaly_labels = iso_forest.fit_predict(scaled_features)
    anomaly_scores = iso_forest.score_samples(scaled_features)

    # Statistical analysis
    z_scores = np.abs(stats.zscore(feature_matrix, axis=0))
    statistical_anomalies = np.any(z_scores > 3, axis=1)

    return {
        "anomaly_labels": anomaly_labels,
        "anomaly_scores": anomaly_scores,
        "n_anomalies": int(np.sum(anomaly_labels == -1)),
        "anomaly_percentage": float(np.sum(anomaly_labels == -1) / len(anomaly_labels) * 100),
        "statistical_anomalies": statistical_anomalies,
        "n_statistical_anomalies": int(np.sum(statistical_anomalies)),
    }


def analyze_patterns_and_trends(results: List[Dict[str, Any]], df_features: pd.DataFrame) -> Dict[str, Any]:
    """Analyze patterns and trends in the data"""
    # Time series analysis
    df_results = pd.DataFrame(results)
    df_results["timestamp"] = pd.to_datetime(df_results["execution_time"])
    df_results = df_results.sort_values("timestamp")

    # Clean and convert score_value to numeric where possible
    def clean_score_value(x):
        """Convert score values to numeric for analysis"""
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return 0.0
        if isinstance(x, bool):
            return float(x)
        if isinstance(x, (int, float)):
            return float(x)
        if isinstance(x, str):
            # Handle concatenated strings like '0.50.50.5' by taking the first number
            try:
                import re

                numbers = re.findall(r"[\d.]+", str(x))
                if numbers:
                    return float(numbers[0])
                return 0.0
            except Exception:
                return 0.0
        return 0.0

    df_results["score_value_numeric"] = df_results["score_value"].apply(clean_score_value)

    # Daily aggregations with cleaned numeric values
    daily_stats = (
        df_results.groupby(df_results["timestamp"].dt.date)
        .agg({"score_value_numeric": "mean", "execution_id": "count"})
        .rename(columns={"execution_id": "test_count", "score_value_numeric": "score_value"})
    )

    # Calculate rolling statistics
    window_size = 7
    daily_stats["rolling_mean"] = daily_stats["score_value"].rolling(window=window_size, min_periods=1).mean()
    daily_stats["rolling_std"] = daily_stats["score_value"].rolling(window=window_size, min_periods=1).std()

    # Trend analysis
    if len(daily_stats) > 1:
        x = np.arange(len(daily_stats))
        y = daily_stats["score_value"].values
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        trend = {
            "slope": float(slope),
            "direction": "increasing" if slope > 0 else "decreasing",
            "r_squared": float(r_value**2),
            "p_value": float(p_value),
        }
    else:
        trend = {"slope": 0, "direction": "stable", "r_squared": 0, "p_value": 1}

    # Correlation analysis
    correlation_matrix = df_features.corr()

    # Find strongest correlations with violations
    if "is_violation" in df_features.columns:
        violation_correlations = correlation_matrix["is_violation"].sort_values(ascending=False)
        top_correlations = violation_correlations[1:6].to_dict()  # Exclude self-correlation
    else:
        top_correlations = {}

    return {
        "daily_stats": daily_stats,
        "trend": trend,
        "correlation_matrix": correlation_matrix,
        "top_correlations": top_correlations,
    }


# --- Visualization Functions ---


def render_ml_overview(clustering_results: Dict[str, Any], anomaly_results: Dict[str, Any]):
    """Render ML analysis overview"""
    st.header("🤖 Machine Learning Analysis Overview")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        n_clusters = len(clustering_results.get("cluster_stats", {}))
        st.metric("Data Clusters", n_clusters, help="Number of distinct patterns identified")

    with col2:
        n_anomalies = anomaly_results.get("n_anomalies", 0)
        st.metric("Anomalies Detected", n_anomalies, help="Unusual patterns in the data")

    with col3:
        anomaly_rate = anomaly_results.get("anomaly_percentage", 0)
        st.metric("Anomaly Rate", f"{anomaly_rate:.1f}%", help="Percentage of anomalous results")

    with col4:
        explained_var = sum(clustering_results.get("pca_explained_variance", [])) * 100
        st.metric("Variance Explained", f"{explained_var:.1f}%", help="By top 3 principal components")

    with col5:
        statistical_anomalies = anomaly_results.get("n_statistical_anomalies", 0)
        st.metric("Statistical Outliers", statistical_anomalies, help="Based on z-score analysis")


def render_clustering_visualization(
    results: List[Dict[str, Any]], clustering_results: Dict[str, Any], df_features: pd.DataFrame
):
    """Render clustering visualization"""
    st.header("🎯 Result Clustering Analysis")

    pca_features = clustering_results.get("pca_features", [])
    kmeans_labels = clustering_results.get("kmeans_labels", [])

    if len(pca_features) == 0:
        st.info("Insufficient data for clustering visualization")
        return

    col1, col2 = st.columns(2)

    with col1:
        # 3D scatter plot of clusters
        if pca_features.shape[1] >= 3:
            fig = go.Figure(
                data=[
                    go.Scatter3d(
                        x=pca_features[:, 0],
                        y=pca_features[:, 1],
                        z=pca_features[:, 2],
                        mode="markers",
                        marker=dict(
                            size=5,
                            color=kmeans_labels,
                            colorscale="Viridis",
                            showscale=True,
                            colorbar=dict(title="Cluster"),
                        ),
                        text=[f"Cluster {label}" for label in kmeans_labels],
                        hoverinfo="text",
                    )
                ]
            )

            fig.update_layout(
                title="3D Cluster Visualization (PCA)",
                scene=dict(xaxis_title="PC1", yaxis_title="PC2", zaxis_title="PC3"),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            # 2D visualization fallback
            fig = px.scatter(
                x=pca_features[:, 0],
                y=pca_features[:, 1] if pca_features.shape[1] > 1 else np.zeros(len(pca_features)),
                color=kmeans_labels,
                title="2D Cluster Visualization (PCA)",
                labels={"x": "PC1", "y": "PC2", "color": "Cluster"},
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Cluster composition
        cluster_stats = clustering_results.get("cluster_stats", {})

        if cluster_stats:
            cluster_data = pd.DataFrame(
                [
                    {"Cluster": k.replace("cluster_", "Cluster "), "Size": v["size"], "Percentage": v["percentage"]}
                    for k, v in cluster_stats.items()
                ]
            )

            fig = px.pie(cluster_data, values="Size", names="Cluster", title="Cluster Distribution", hole=0.4)
            st.plotly_chart(fig, use_container_width=True)

    # Cluster characteristics
    st.subheader("📊 Cluster Characteristics")

    # Analyze each cluster
    cluster_analysis = []
    for cluster_id in range(len(cluster_stats)):
        cluster_mask = kmeans_labels == cluster_id
        cluster_results = [r for r, m in zip(results, cluster_mask) if m]

        if cluster_results:
            # Calculate cluster statistics
            violations = sum(1 for r in cluster_results if r.get("score_value") is True)
            violation_rate = violations / len(cluster_results) * 100 if cluster_results else 0

            # Most common scorer in cluster
            scorer_counts = Counter(r.get("metadata", {}).get("scorer_type", "Unknown") for r in cluster_results)
            most_common_scorer = scorer_counts.most_common(1)[0][0] if scorer_counts else "Unknown"

            cluster_analysis.append(
                {
                    "Cluster": f"Cluster {cluster_id}",
                    "Size": len(cluster_results),
                    "Violation Rate": f"{violation_rate:.1f}%",
                    "Primary Scorer": most_common_scorer,
                    "Avg Hour": f"{np.mean([r.get('metadata', {}).get('hour', 12) for r in cluster_results]):.1f}",
                }
            )

    if cluster_analysis:
        df_cluster_analysis = pd.DataFrame(cluster_analysis)
        st.dataframe(df_cluster_analysis, use_container_width=True, hide_index=True)


def render_anomaly_detection(results: List[Dict[str, Any]], anomaly_results: Dict[str, Any], df_features: pd.DataFrame):
    """Render anomaly detection results"""
    st.header("🔍 Anomaly Detection")

    anomaly_labels = anomaly_results.get("anomaly_labels", [])
    anomaly_scores = anomaly_results.get("anomaly_scores", [])

    if len(anomaly_labels) == 0:
        st.info("No anomaly detection results available")
        return

    col1, col2 = st.columns(2)

    with col1:
        # Anomaly score distribution
        fig = go.Figure()

        # Normal points
        normal_mask = anomaly_labels != -1
        fig.add_trace(go.Histogram(x=anomaly_scores[normal_mask], name="Normal", marker_color="blue", opacity=0.7))

        # Anomalies
        anomaly_mask = anomaly_labels == -1
        if np.any(anomaly_mask):
            fig.add_trace(
                go.Histogram(x=anomaly_scores[anomaly_mask], name="Anomalies", marker_color="red", opacity=0.7)
            )

        fig.update_layout(
            title="Anomaly Score Distribution", xaxis_title="Anomaly Score", yaxis_title="Count", barmode="overlay"
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Feature importance for anomalies
        if np.any(anomaly_mask):
            # Calculate feature differences for anomalies
            normal_features = df_features[normal_mask].mean()
            anomaly_features = df_features[anomaly_mask].mean()
            feature_diff = (anomaly_features - normal_features).abs().sort_values(ascending=False)

            top_features = feature_diff.head(10)

            fig = px.bar(
                x=top_features.values,
                y=top_features.index,
                orientation="h",
                title="Top Anomaly Features",
                labels={"x": "Difference from Normal", "y": "Feature"},
            )
            st.plotly_chart(fig, use_container_width=True)

    # Anomaly details
    st.subheader("🚨 Anomaly Details")

    anomaly_indices = np.where(anomaly_labels == -1)[0]
    if len(anomaly_indices) > 0:
        anomaly_data = []
        for idx in anomaly_indices[:20]:  # Show top 20
            if idx < len(results):
                result = results[idx]
                metadata = result.get("metadata", {})
                anomaly_data.append(
                    {
                        "Time": result.get("execution_time", "Unknown")[:19],
                        "Scorer": metadata.get("scorer_name", "Unknown"),
                        "Generator": metadata.get("generator_name", "Unknown"),
                        "Score": str(result.get("score_value", "N/A")),
                        "Anomaly Score": f"{anomaly_scores[idx]:.3f}",
                    }
                )

        df_anomalies = pd.DataFrame(anomaly_data)
        st.dataframe(df_anomalies, use_container_width=True, hide_index=True)


def render_pattern_trends(pattern_analysis: Dict[str, Any]):
    """Render pattern and trend analysis"""
    st.header("📈 Pattern & Trend Analysis")

    # Trend overview
    trend = pattern_analysis.get("trend", {})

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        direction = trend.get("direction", "stable")
        icon = "📈" if direction == "increasing" else "📉" if direction == "decreasing" else "➡️"
        st.metric("Trend Direction", f"{icon} {direction.capitalize()}")

    with col2:
        slope = trend.get("slope", 0)
        st.metric("Trend Strength", f"{abs(slope):.4f}", help="Rate of change per day")

    with col3:
        r_squared = trend.get("r_squared", 0)
        st.metric("R-squared", f"{r_squared:.3f}", help="Goodness of fit")

    with col4:
        p_value = trend.get("p_value", 1)
        significance = "Significant" if p_value < 0.05 else "Not Significant"
        st.metric("Statistical Significance", significance)

    # Time series visualization
    daily_stats = pattern_analysis.get("daily_stats")

    if daily_stats is not None and len(daily_stats) > 0:
        st.subheader("📊 Time Series Analysis")

        # Reset index for plotting
        daily_stats_plot = daily_stats.reset_index()

        fig = make_subplots(
            rows=2, cols=1, subplot_titles=("Daily Violation Rate", "Test Volume"), vertical_spacing=0.1
        )

        # Violation rate
        fig.add_trace(
            go.Scatter(
                x=daily_stats_plot["timestamp"],
                y=daily_stats_plot["score_value"],
                mode="lines+markers",
                name="Daily Rate",
                line=dict(color="red", width=2),
            ),
            row=1,
            col=1,
        )

        # Rolling average
        if "rolling_mean" in daily_stats_plot.columns:
            fig.add_trace(
                go.Scatter(
                    x=daily_stats_plot["timestamp"],
                    y=daily_stats_plot["rolling_mean"],
                    mode="lines",
                    name="7-Day Average",
                    line=dict(color="orange", width=2, dash="dash"),
                ),
                row=1,
                col=1,
            )

        # Test volume
        fig.add_trace(
            go.Bar(
                x=daily_stats_plot["timestamp"],
                y=daily_stats_plot["test_count"],
                name="Test Count",
                marker_color="lightblue",
            ),
            row=2,
            col=1,
        )

        fig.update_xaxes(title_text="Date", row=2, col=1)
        fig.update_yaxes(title_text="Rate", row=1, col=1)
        fig.update_yaxes(title_text="Count", row=2, col=1)

        fig.update_layout(height=600, showlegend=True)
        st.plotly_chart(fig, use_container_width=True)

    # Correlation heatmap
    st.subheader("🔗 Feature Correlations")

    correlation_matrix = pattern_analysis.get("correlation_matrix")
    if correlation_matrix is not None and len(correlation_matrix) > 0:
        # Select important features for visualization
        important_features = [
            "is_violation",
            "score_value_numeric",
            "hour",
            "day_of_week",
            "batch_position",
            "rationale_length",
            "has_critical_keywords",
        ]

        # Filter to available features
        available_features = [f for f in important_features if f in correlation_matrix.columns]

        if len(available_features) > 1:
            corr_subset = correlation_matrix.loc[available_features, available_features]

            fig = px.imshow(
                corr_subset,
                labels=dict(color="Correlation"),
                x=available_features,
                y=available_features,
                color_continuous_scale="RdBu_r",
                zmin=-1,
                zmax=1,
                title="Feature Correlation Matrix",
            )
            st.plotly_chart(fig, use_container_width=True)

            # Top correlations with violations
            top_corr = pattern_analysis.get("top_correlations", {})
            if top_corr:
                st.markdown("**Top Correlations with Violations:**")
                for feature, corr in list(top_corr.items())[:5]:
                    st.text(f"• {feature}: {corr:.3f}")


def render_predictive_insights(results: List[Dict[str, Any]], pattern_analysis: Dict[str, Any]):
    """Render predictive insights and recommendations"""
    st.header("💡 Predictive Insights & Recommendations")

    # Risk prediction model (simplified)
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🎯 Risk Factors")

        # Analyze risk factors
        risk_factors = []

        # Time-based risk
        hour_violations = defaultdict(list)
        for r in results:
            hour = datetime.fromisoformat(
                r.get("execution_time", datetime.now().isoformat()).replace("Z", "+00:00")
            ).hour
            if r.get("score_value") is True:
                hour_violations[hour].append(1)

        high_risk_hours = [
            h for h, v in hour_violations.items() if len(v) > np.mean([len(v) for v in hour_violations.values()])
        ]

        if high_risk_hours:
            risk_factors.append(
                {
                    "Factor": "High-Risk Hours",
                    "Description": f"Hours {', '.join(map(str, sorted(high_risk_hours)))}",
                    "Impact": "High",
                }
            )

        # Scorer-based risk
        scorer_risks = defaultdict(int)
        for r in results:
            if r.get("score_value") is True:
                scorer = r.get("metadata", {}).get("scorer_type", "Unknown")
                scorer_risks[scorer] += 1

        high_risk_scorers = [s for s, c in scorer_risks.items() if c > np.mean(list(scorer_risks.values()))]

        if high_risk_scorers:
            risk_factors.append(
                {"Factor": "High-Risk Scorers", "Description": ", ".join(high_risk_scorers[:3]), "Impact": "Medium"}
            )

        if risk_factors:
            df_risks = pd.DataFrame(risk_factors)
            st.dataframe(df_risks, use_container_width=True, hide_index=True)

    with col2:
        st.subheader("📋 Recommendations")

        # Generate recommendations based on analysis
        recommendations = []

        # Trend-based recommendations
        trend = pattern_analysis.get("trend", {})
        if trend.get("direction") == "increasing" and trend.get("p_value", 1) < 0.05:
            recommendations.append(
                {
                    "Priority": "🔴 High",
                    "Action": "Investigate increasing violation trend",
                    "Details": "Statistically significant upward trend detected",
                }
            )

        # Anomaly-based recommendations
        anomaly_rate = len([r for r in results if r.get("is_anomaly", False)]) / len(results) * 100 if results else 0
        if anomaly_rate > 5:
            recommendations.append(
                {
                    "Priority": "🟡 Medium",
                    "Action": "Review anomalous patterns",
                    "Details": f"{anomaly_rate:.1f}% anomaly rate detected",
                }
            )

        # Time-based recommendations
        if high_risk_hours:
            recommendations.append(
                {
                    "Priority": "🟡 Medium",
                    "Action": "Monitor high-risk time periods",
                    "Details": f"Increased violations during specific hours",
                }
            )

        if recommendations:
            df_recommendations = pd.DataFrame(recommendations)
            st.dataframe(df_recommendations, use_container_width=True, hide_index=True)
        else:
            st.success("✅ No critical issues detected")

    # Forecast visualization (simplified)
    st.subheader("📊 Violation Rate Forecast")

    daily_stats = pattern_analysis.get("daily_stats")
    if daily_stats is not None and len(daily_stats) > 7:
        # Simple linear forecast
        n_days = len(daily_stats)
        x = np.arange(n_days)
        y = daily_stats["score_value"].values

        # Fit linear model
        slope = trend.get("slope", 0)
        intercept = np.mean(y) - slope * np.mean(x)

        # Generate forecast
        forecast_days = 7
        future_x = np.arange(n_days, n_days + forecast_days)
        forecast_y = slope * future_x + intercept

        # Create visualization
        fig = go.Figure()

        # Historical data
        fig.add_trace(
            go.Scatter(x=daily_stats.index, y=y, mode="lines+markers", name="Historical", line=dict(color="blue"))
        )

        # Forecast
        future_dates = pd.date_range(start=daily_stats.index[-1] + timedelta(days=1), periods=forecast_days)
        fig.add_trace(
            go.Scatter(
                x=future_dates, y=forecast_y, mode="lines+markers", name="Forecast", line=dict(color="red", dash="dash")
            )
        )

        # Confidence interval (simplified)
        std = daily_stats["score_value"].std()
        fig.add_trace(
            go.Scatter(
                x=future_dates,
                y=forecast_y + 2 * std,
                mode="lines",
                line=dict(color="red", dash="dot", width=1),
                showlegend=False,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=future_dates,
                y=forecast_y - 2 * std,
                mode="lines",
                line=dict(color="red", dash="dot", width=1),
                fill="tonexty",
                fillcolor="rgba(255,0,0,0.1)",
                name="95% Confidence",
            )
        )

        fig.update_layout(title="7-Day Violation Rate Forecast", xaxis_title="Date", yaxis_title="Violation Rate")
        st.plotly_chart(fig, use_container_width=True)


# --- Main Dashboard Function ---


def main():
    """Main advanced analytics dashboard with ML insights"""
    logger.debug("Advanced Analytics Dashboard loading.")
    st.set_page_config(
        page_title="ViolentUTF Advanced Dashboard", page_icon="🧬", layout="wide", initial_sidebar_state="expanded"
    )

    # Authentication and sidebar
    handle_authentication_and_sidebar("Advanced Dashboard")

    # Check authentication
    has_keycloak_token = bool(st.session_state.get("access_token"))
    has_env_credentials = bool(os.getenv("KEYCLOAK_USERNAME"))

    if not has_keycloak_token and not has_env_credentials:
        st.warning(
            "⚠️ Authentication required: Please log in via Keycloak SSO or configure KEYCLOAK_USERNAME in environment."
        )
        st.info("💡 For local development, you can set KEYCLOAK_USERNAME and KEYCLOAK_PASSWORD in your .env file")
        return

    # Ensure API token exists
    if not st.session_state.get("api_token"):
        with st.spinner("Generating API token..."):
            api_token = create_compatible_api_token()
            if not api_token:
                st.error("❌ Failed to generate API token. Please try refreshing the page.")
                return

    # Page header
    st.title("🧬 ViolentUTF Advanced Dashboard")
    st.markdown("*Machine learning insights and predictive analytics for AI security testing*")

    # Sidebar controls
    with st.sidebar:
        st.header("⚙️ Analytics Controls")

        # Time range
        days_back = st.slider(
            "Analysis Time Range (days)",
            min_value=7,
            max_value=90,
            value=30,
            help="Number of days to include in analysis",
        )

        # ML parameters
        st.subheader("ML Parameters")

        n_clusters = st.slider(
            "Number of Clusters", min_value=3, max_value=10, value=5, help="Number of clusters for K-means"
        )

        anomaly_threshold = st.slider(
            "Anomaly Threshold (%)", min_value=1, max_value=20, value=10, help="Expected percentage of anomalies"
        )

        # Analysis options
        st.subheader("Analysis Options")

        show_clustering = st.checkbox("Show Clustering", value=True)
        show_anomalies = st.checkbox("Show Anomalies", value=True)
        show_predictions = st.checkbox("Show Predictions", value=True)

        # Refresh button
        if st.button("🔃 Refresh Analysis", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.divider()

        # Info section
        st.info(
            "**Advanced Features:**\n"
            "- Unsupervised clustering\n"
            "- Anomaly detection\n"
            "- Trend analysis\n"
            "- Risk prediction\n"
            "- Pattern recognition"
        )

    # Load and process data
    with st.spinner("🔄 Loading and processing data for ML analysis..."):
        # Load comprehensive data
        data = load_all_execution_data(days_back)

        executions = data.get("executions", [])
        results = data.get("results", [])

        if not results:
            st.warning("📊 No data available for analysis in the selected time range.")
            st.info(
                "To generate data:\n"
                "1. Run scorer tests with generators\n"
                "2. Execute full orchestrator runs\n"
                "3. Return here for advanced analysis"
            )
            return

        # Prepare feature matrix
        df_features, feature_matrix = prepare_feature_matrix(results)

        # Perform ML analysis
        clustering_results = perform_clustering_analysis(feature_matrix, n_clusters)
        anomaly_results = perform_anomaly_detection(feature_matrix, anomaly_threshold / 100)
        pattern_analysis = analyze_patterns_and_trends(results, df_features)

        # Add anomaly labels to results
        anomaly_labels = anomaly_results.get("anomaly_labels", [])
        for i, result in enumerate(results):
            if i < len(anomaly_labels):
                result["is_anomaly"] = anomaly_labels[i] == -1

    # Display success message
    st.success(f"✅ Analyzed {len(results)} results from {len(executions)} executions over {days_back} days")

    # Render dashboard sections
    tabs = st.tabs(["🤖 ML Overview", "🎯 Clustering", "🔍 Anomalies", "📈 Patterns & Trends", "💡 Insights"])

    with tabs[0]:
        render_ml_overview(clustering_results, anomaly_results)

    with tabs[1]:
        if show_clustering:
            render_clustering_visualization(results, clustering_results, df_features)
        else:
            st.info("Clustering analysis is disabled. Enable it in the sidebar.")

    with tabs[2]:
        if show_anomalies:
            render_anomaly_detection(results, anomaly_results, df_features)
        else:
            st.info("Anomaly detection is disabled. Enable it in the sidebar.")

    with tabs[3]:
        render_pattern_trends(pattern_analysis)

    with tabs[4]:
        if show_predictions:
            render_predictive_insights(results, pattern_analysis)
        else:
            st.info("Predictive insights are disabled. Enable them in the sidebar.")


if __name__ == "__main__":
    main()
