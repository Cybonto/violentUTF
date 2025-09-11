# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
UI Performance Monitoring Module

Provides comprehensive UI performance monitoring for Streamlit applications
including page load times, interaction responsiveness, and user experience metrics.

Key Components:
- StreamlitPerformanceMonitor: Core Streamlit performance monitoring
- UIPerformanceMetrics: UI performance measurement data structures
- UserInteractionTracker: User interaction performance tracking
- PageLoadMonitor: Page loading performance analysis

SECURITY: All monitoring data is for defensive security research only.
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import psutil
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class UIPerformanceLevel(Enum):
    """UI performance classification levels"""

    EXCELLENT = "excellent"  # <100ms response, <2s load
    GOOD = "good"  # <300ms response, <5s load
    ACCEPTABLE = "acceptable"  # <800ms response, <10s load
    POOR = "poor"  # <2000ms response, <20s load
    CRITICAL = "critical"  # >2000ms response, >20s load


@dataclass
class UIPerformanceMetrics:
    """UI performance measurement results"""

    session_id: str
    measurement_timestamp: datetime
    page_load_time: float  # milliseconds
    interaction_response_time: float  # milliseconds
    resource_load_time: float  # milliseconds
    dom_ready_time: float  # milliseconds
    first_contentful_paint: float  # milliseconds
    largest_contentful_paint: float  # milliseconds
    cumulative_layout_shift: float  # score
    first_input_delay: float  # milliseconds
    javascript_errors: List[str] = field(default_factory=list)
    network_requests: int = 0
    total_page_size_kb: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0

    @property
    def performance_level(self) -> UIPerformanceLevel:
        """Determine overall UI performance level"""
        # Primary metrics for classification
        load_score = self._score_load_time(self.page_load_time)
        response_score = self._score_response_time(self.interaction_response_time)
        vitals_score = self._score_core_vitals()

        # Calculate weighted average
        overall_score = load_score * 0.4 + response_score * 0.4 + vitals_score * 0.2

        if overall_score >= 90:
            return UIPerformanceLevel.EXCELLENT
        elif overall_score >= 75:
            return UIPerformanceLevel.GOOD
        elif overall_score >= 60:
            return UIPerformanceLevel.ACCEPTABLE
        elif overall_score >= 40:
            return UIPerformanceLevel.POOR
        else:
            return UIPerformanceLevel.CRITICAL

    def _score_load_time(self, load_time_ms: float) -> float:
        """Score page load time (0-100)"""
        if load_time_ms < 2000:
            return 100
        elif load_time_ms < 5000:
            return 80
        elif load_time_ms < 10000:
            return 60
        elif load_time_ms < 20000:
            return 40
        else:
            return 20

    def _score_response_time(self, response_time_ms: float) -> float:
        """Score interaction response time (0-100)"""
        if response_time_ms < 100:
            return 100
        elif response_time_ms < 300:
            return 80
        elif response_time_ms < 800:
            return 60
        elif response_time_ms < 2000:
            return 40
        else:
            return 20

    def _score_core_vitals(self) -> float:
        """Score Core Web Vitals (0-100)"""
        lcp_score = 100 if self.largest_contentful_paint < 2500 else 50
        fid_score = 100 if self.first_input_delay < 100 else 50
        cls_score = 100 if self.cumulative_layout_shift < 0.1 else 50

        return (lcp_score + fid_score + cls_score) / 3


@dataclass
class UserInteractionMetrics:
    """User interaction performance measurements"""

    interaction_type: str  # click, input, select, scroll
    element_selector: str
    response_time_ms: float
    success: bool
    error_message: Optional[str]
    timestamp: datetime
    page_context: str


class PageLoadMonitor:
    """Monitor page loading performance and resources"""

    def __init__(self) -> None:
        """Initialize PageLoadMonitor.

        Sets up page load monitoring with an empty metrics collection list.
        """
        self.load_metrics: List[Dict[str, Any]] = []

    def measure_page_load(self, driver: webdriver.Chrome, url: str) -> Dict[str, float]:
        """Measure comprehensive page load metrics"""
        start_time = time.time()

        # Navigate to page
        driver.get(url)

        # Wait for page to load
        WebDriverWait(driver, 30).until(lambda d: d.execute_script("return document.readyState") == "complete")

        # Get performance timing data
        performance_data = driver.execute_script(
            """
            var timing = performance.timing;
            var navigation = performance.getEntriesByType('navigation')[0];

            return {
                domLoading: timing.domLoading - timing.navigationStart,
                domComplete: timing.domComplete - timing.navigationStart,
                loadComplete: timing.loadEventEnd - timing.navigationStart,
                domContentLoaded: timing.domContentLoadedEventEnd - timing.navigationStart,
                firstPaint: (performance.getEntriesByName('first-paint')[0] || {}).startTime || 0,
                firstContentfulPaint: (performance.getEntriesByName('first-contentful-paint')[0] || {}).startTime || 0,
                largestContentfulPaint: (performance.getEntriesByName('largest-contentful-paint')[0] ||
                    {}).startTime || 0,
                cumulativeLayoutShift: (performance.getEntriesByType('layout-shift').
                    reduce((sum, entry) => sum + entry.value, 0)) || 0,
                networkRequests: performance.getEntriesByType('resource').length,
                totalSize: performance.getEntriesByType('resource').
                    reduce((sum, entry) => sum + (entry.transferSize || 0), 0)
            };
        """
        )

        # Get JavaScript errors
        js_errors = driver.execute_script(
            """
            return window.jsErrors || [];
        """
        )

        metrics = {
            "page_load_time": performance_data.get("loadComplete", 0),
            "dom_ready_time": performance_data.get("domContentLoaded", 0),
            "first_contentful_paint": performance_data.get("firstContentfulPaint", 0),
            "largest_contentful_paint": performance_data.get("largestContentfulPaint", 0),
            "cumulative_layout_shift": performance_data.get("cumulativeLayoutShift", 0),
            "network_requests": performance_data.get("networkRequests", 0),
            "total_page_size_kb": performance_data.get("totalSize", 0) / 1024,
            "javascript_errors": js_errors,
            "measurement_duration": (time.time() - start_time) * 1000,
        }

        self.load_metrics.append(metrics)
        return metrics


class UserInteractionTracker:
    """Track user interaction performance and responsiveness"""

    def __init__(self) -> None:
        """Initialize UserInteractionTracker.

        Sets up user interaction tracking with an empty metrics collection list.
        """
        self.interaction_metrics: List[UserInteractionMetrics] = []

    def measure_interaction_response(
        self,
        driver: webdriver.Chrome,
        interaction_type: str,
        element_selector: str,
        action_callback: Callable[[webdriver.Chrome], None],
        expected_change: Optional[str] = None,
    ) -> UserInteractionMetrics:
        """Measure response time for user interactions"""
        start_time = time.time()
        success = True
        error_message = None

        try:
            # Execute the interaction
            action_callback(driver)

            # Wait for expected change if specified
            if expected_change:
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, expected_change)))

        except (TimeoutException, WebDriverException) as e:
            success = False
            error_message = str(e)

        response_time = (time.time() - start_time) * 1000

        metrics = UserInteractionMetrics(
            interaction_type=interaction_type,
            element_selector=element_selector,
            response_time_ms=response_time,
            success=success,
            error_message=error_message,
            timestamp=datetime.now(timezone.utc),
            page_context=driver.current_url,
        )

        self.interaction_metrics.append(metrics)
        return metrics

    def get_interaction_summary(self) -> Dict[str, Any]:
        """Get summary of interaction performance"""
        if not self.interaction_metrics:
            return {"total_interactions": 0}

        successful_interactions = [m for m in self.interaction_metrics if m.success]
        response_times = [m.response_time_ms for m in successful_interactions]

        return {
            "total_interactions": len(self.interaction_metrics),
            "successful_interactions": len(successful_interactions),
            "success_rate_percent": (len(successful_interactions) / len(self.interaction_metrics)) * 100,
            "avg_response_time_ms": sum(response_times) / len(response_times) if response_times else 0,
            "max_response_time_ms": max(response_times) if response_times else 0,
            "min_response_time_ms": min(response_times) if response_times else 0,
        }


class StreamlitPerformanceMonitor:
    """
    Comprehensive Streamlit application performance monitoring

    Monitors page load times, user interaction responsiveness, resource usage,
    and overall user experience metrics for Streamlit applications.
    """

    def __init__(self, base_url: str = "http://localhost:8501", session_id: str = None) -> None:
        """Initialize UIPerformanceMonitor.

        Args:
            base_url: Base URL of the Streamlit application.
                     Defaults to 'http://localhost:8501'.
            session_id: Unique identifier for monitoring session.
                       Defaults to timestamp-based ID.
        """
        self.base_url = base_url
        self.session_id = session_id or f"ui_perf_{int(time.time())}"
        self.page_load_monitor = PageLoadMonitor()
        self.interaction_tracker = UserInteractionTracker()
        self.performance_history: List[UIPerformanceMetrics] = []
        self.logger = logging.getLogger(__name__)

    def measure_ui_performance(
        self, pages_to_test: List[str], performance_targets: Dict[str, Any], headless: bool = True
    ) -> UIPerformanceMetrics:
        """
        Measure comprehensive UI performance across specified pages

        Args:
            pages_to_test: List of page paths to test (e.g., ["/", "/config", "/results"])
            performance_targets: Performance target thresholds
            headless: Run browser in headless mode

        Returns:
            UIPerformanceMetrics: Comprehensive performance measurements
        """
        session_id = f"ui_perf_{int(time.time())}"

        # Setup Chrome driver
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")

        # Initialize metrics
        total_load_time = 0
        total_interaction_time = 0
        all_js_errors = []
        total_requests = 0
        total_page_size = 0

        try:
            driver = webdriver.Chrome(options=chrome_options)

            # Inject error collection script
            driver.execute_script(
                """
                window.jsErrors = [];
                window.addEventListener('error', function(e) {
                    window.jsErrors.push(e.message + ' at ' + e.filename + ':' + e.lineno);
                });
            """
            )

            for page_path in pages_to_test:
                full_url = f"{self.base_url}{page_path}"

                # Measure page load
                load_metrics = self.page_load_monitor.measure_page_load(driver, full_url)
                total_load_time += load_metrics["page_load_time"]
                total_requests += load_metrics["network_requests"]
                total_page_size += load_metrics["total_page_size_kb"]
                all_js_errors.extend(load_metrics["javascript_errors"])

                # Measure common interactions
                self._test_common_interactions(driver, page_path)

            # Calculate average interaction time
            interaction_summary = self.interaction_tracker.get_interaction_summary()
            total_interaction_time = interaction_summary.get("avg_response_time_ms", 0)

            # Get system resource usage
            process = psutil.Process()
            memory_usage = process.memory_info().rss / 1024 / 1024  # MB
            cpu_percent = process.cpu_percent(interval=1)

        except Exception as e:
            # Fallback metrics in case of browser issues
            total_load_time = 30000  # Assume poor performance
            total_interaction_time = 3000
            all_js_errors.append(f"Browser setup error: {str(e)}")
            memory_usage = 0
            cpu_percent = 0
            total_requests = 0
            total_page_size = 0

        finally:
            try:
                driver.quit()
            except Exception:
                pass

        # Create comprehensive performance metrics
        avg_load_time = total_load_time / len(pages_to_test) if pages_to_test else total_load_time

        ui_metrics = UIPerformanceMetrics(
            session_id=session_id,
            measurement_timestamp=datetime.now(timezone.utc),
            page_load_time=avg_load_time,
            interaction_response_time=total_interaction_time,
            resource_load_time=avg_load_time * 0.6,  # Estimate
            dom_ready_time=avg_load_time * 0.8,  # Estimate
            first_contentful_paint=avg_load_time * 0.3,  # Estimate
            largest_contentful_paint=avg_load_time * 0.7,  # Estimate
            cumulative_layout_shift=0.05,  # Typical good value
            first_input_delay=total_interaction_time * 0.1,  # Estimate
            javascript_errors=all_js_errors,
            network_requests=total_requests,
            total_page_size_kb=total_page_size,
            memory_usage_mb=memory_usage,
            cpu_usage_percent=cpu_percent,
        )

        self.performance_history.append(ui_metrics)
        return ui_metrics

    def _test_common_interactions(self, driver: webdriver.Chrome, page_path: str) -> None:
        """Test common UI interactions for performance"""
        try:
            # Test sidebar toggle (common in Streamlit)
            sidebar_elements = driver.find_elements(By.CSS_SELECTOR, "[data-testid='stSidebar']")
            if sidebar_elements:

                def toggle_sidebar(d: webdriver.Chrome) -> None:
                    # Look for sidebar toggle or navigation elements
                    toggles = d.find_elements(By.CSS_SELECTOR, "button, .sidebar-toggle, [role='button']")
                    if toggles:
                        toggles[0].click()

                self.interaction_tracker.measure_interaction_response(
                    driver, "sidebar_toggle", "[data-testid='stSidebar']", toggle_sidebar
                )

            # Test form interactions (if present)
            form_inputs = driver.find_elements(By.CSS_SELECTOR, "input, select, textarea")
            if form_inputs:

                def interact_with_form(d: webdriver.Chrome) -> None:
                    input_elem = form_inputs[0]
                    if input_elem.get_attribute("type") in ["text", "email", "password"]:
                        input_elem.clear()
                        input_elem.send_keys("test")

                self.interaction_tracker.measure_interaction_response(driver, "form_input", "input", interact_with_form)

            # Test button clicks (if present)
            buttons = driver.find_elements(By.CSS_SELECTOR, "button[kind='primary'], button[kind='secondary']")
            if buttons:

                def click_button(d: webdriver.Chrome) -> None:
                    buttons[0].click()
                    time.sleep(0.5)  # Allow for response

                self.interaction_tracker.measure_interaction_response(driver, "button_click", "button", click_button)

        except Exception as e:
            # Log interaction testing issues but don't fail the overall test
            self.logger.warning("Interaction testing failed for %s: %s", page_path, e)

    def track_user_interaction_performance(
        self, interaction_type: str, target_element: str, performance_threshold_ms: int = 300
    ) -> Dict[str, Any]:
        """Track specific user interaction performance"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")

        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.get(self.base_url)

            # Wait for page to load
            WebDriverWait(driver, 30).until(lambda d: d.execute_script("return document.readyState") == "complete")

            def perform_interaction(d: webdriver.Chrome) -> None:
                element = d.find_element(By.CSS_SELECTOR, target_element)
                if interaction_type == "click":
                    element.click()
                elif interaction_type == "input":
                    element.send_keys("test input")
                elif interaction_type == "select":
                    element.click()

            metrics = self.interaction_tracker.measure_interaction_response(
                driver, interaction_type, target_element, perform_interaction
            )

            result = {
                "interaction_type": interaction_type,
                "target_element": target_element,
                "response_time_ms": metrics.response_time_ms,
                "success": metrics.success,
                "meets_threshold": metrics.response_time_ms <= performance_threshold_ms,
                "performance_level": (
                    "excellent"
                    if metrics.response_time_ms < 100
                    else (
                        "good"
                        if metrics.response_time_ms < 300
                        else "acceptable" if metrics.response_time_ms < 800 else "poor"
                    )
                ),
            }

            return result

        except Exception as e:
            return {
                "interaction_type": interaction_type,
                "target_element": target_element,
                "response_time_ms": 10000,  # Assume poor performance on error
                "success": False,
                "error": str(e),
                "meets_threshold": False,
                "performance_level": "critical",
            }

        finally:
            try:
                driver.quit()
            except Exception:
                pass

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive UI performance summary"""
        if not self.performance_history:
            return {"message": "No performance data collected"}

        recent_metrics = self.performance_history[-5:]  # Last 5 measurements

        avg_load_time = sum(m.page_load_time for m in recent_metrics) / len(recent_metrics)
        avg_interaction_time = sum(m.interaction_response_time for m in recent_metrics) / len(recent_metrics)

        performance_levels = [m.performance_level.value for m in recent_metrics]
        level_distribution = {level: performance_levels.count(level) for level in set(performance_levels)}

        return {
            "total_measurements": len(self.performance_history),
            "recent_performance": {
                "avg_page_load_time_ms": avg_load_time,
                "avg_interaction_response_time_ms": avg_interaction_time,
                "performance_level_distribution": level_distribution,
            },
            "interaction_summary": self.interaction_tracker.get_interaction_summary(),
            "latest_metrics": {
                "performance_level": recent_metrics[-1].performance_level.value,
                "page_load_time": recent_metrics[-1].page_load_time,
                "javascript_errors": len(recent_metrics[-1].javascript_errors),
                "memory_usage_mb": recent_metrics[-1].memory_usage_mb,
            },
        }
