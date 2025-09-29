/**
 * Chart Performance Configuration
 * Provides predefined performance profiles for different use cases
 */

export const PerformanceProfiles = {
    // High performance for long-running data visualization
    HIGH_PERFORMANCE: {
        maxDataPoints: 1000,
        decimationThreshold: 2000,
        batchUpdateInterval: 2000,
        enableBatchUpdates: true,
        animation: false,
        pointRadius: 0,
        borderWidth: 1
    },

    // Balanced performance for normal operations
    BALANCED: {
        maxDataPoints: 2000,
        decimationThreshold: 5000,
        batchUpdateInterval: 1000,
        enableBatchUpdates: true,
        animation: false,
        pointRadius: 0,
        borderWidth: 1
    },

    // High quality for detailed analysis (slower but more accurate)
    HIGH_QUALITY: {
        maxDataPoints: 5000,
        decimationThreshold: 10000,
        batchUpdateInterval: 500,
        enableBatchUpdates: true,
        animation: false,
        pointRadius: 1,
        borderWidth: 2
    },

    // Real-time responsive for immediate feedback
    REALTIME: {
        maxDataPoints: 500,
        decimationThreshold: 1000,
        batchUpdateInterval: 200,
        enableBatchUpdates: false,
        animation: false,
        pointRadius: 0,
        borderWidth: 1
    }
};

/**
 * Auto-detect performance profile based on data characteristics
 */
export function getOptimalProfile(expectedDataPoints, updateFrequencyMs, deviceCapability = 'medium') {
    const pointsPerHour = 3600000 / updateFrequencyMs; // Points generated per hour
    const totalExpectedPoints = expectedDataPoints || pointsPerHour * 8; // Assume 8-hour session

    // Device capability adjustment
    const performanceMultiplier = {
        'low': 0.5,
        'medium': 1.0,
        'high': 2.0
    }[deviceCapability] || 1.0;

    if (totalExpectedPoints > 50000 || pointsPerHour > 3600) {
        // Very high data volume - prioritize performance
        return {
            ...PerformanceProfiles.HIGH_PERFORMANCE,
            maxDataPoints: Math.floor(PerformanceProfiles.HIGH_PERFORMANCE.maxDataPoints * performanceMultiplier)
        };
    } else if (totalExpectedPoints > 10000 || pointsPerHour > 360) {
        // High data volume - balanced approach
        return {
            ...PerformanceProfiles.BALANCED,
            maxDataPoints: Math.floor(PerformanceProfiles.BALANCED.maxDataPoints * performanceMultiplier)
        };
    } else if (updateFrequencyMs < 1000) {
        // High frequency updates - real-time profile
        return {
            ...PerformanceProfiles.REALTIME,
            maxDataPoints: Math.floor(PerformanceProfiles.REALTIME.maxDataPoints * performanceMultiplier)
        };
    } else {
        // Normal usage - high quality
        return {
            ...PerformanceProfiles.HIGH_QUALITY,
            maxDataPoints: Math.floor(PerformanceProfiles.HIGH_QUALITY.maxDataPoints * performanceMultiplier)
        };
    }
}

/**
 * Create optimized chart configuration for climate chamber data
 */
export function createOptimizedChartConfig(baseConfig = {}, performanceProfile = null) {
    const profile = performanceProfile || PerformanceProfiles.BALANCED;

    return {
        // Base configuration
        responsive: true,
        maintainAspectRatio: false,

        // Performance optimizations
        animation: profile.animation,

        // Dataset defaults
        datasets: {
            line: {
                pointRadius: profile.pointRadius,
                borderWidth: profile.borderWidth,
                fill: false,
                tension: 0
            }
        },

        // Optimized interaction settings
        interaction: {
            intersect: false,
            mode: 'index'
        },

        // Scales optimization
        scales: {
            x: {
                type: 'linear',
                ticks: {
                    maxTicksLimit: 10 // Limit number of x-axis labels
                }
            },
            y: {
                ticks: {
                    maxTicksLimit: 8 // Limit number of y-axis labels
                }
            }
        },

        // Plugin optimizations
        plugins: {
            legend: {
                labels: {
                    usePointStyle: false // Faster rendering
                }
            }
        },

        // Apply performance profile settings
        ...profile,

        // Override with user config
        ...baseConfig
    };
}

/**
 * Monitor chart performance and suggest optimizations
 */
export class ChartPerformanceMonitor {
    constructor(chartManager) {
        this.chartManager = chartManager;
        this.updateTimes = [];
        this.maxSamples = 50;
        this.warningThreshold = 100; // ms
        this.criticalThreshold = 200; // ms
    }

    /**
     * Record chart update time
     */
    recordUpdateTime(updateDurationMs) {
        this.updateTimes.push(updateDurationMs);

        // Keep only recent samples
        if (this.updateTimes.length > this.maxSamples) {
            this.updateTimes = this.updateTimes.slice(-this.maxSamples);
        }

        // Check for performance issues
        this.checkPerformance();
    }

    /**
     * Get average update time
     */
    getAverageUpdateTime() {
        if (this.updateTimes.length === 0) return 0;
        return this.updateTimes.reduce((sum, time) => sum + time, 0) / this.updateTimes.length;
    }

    /**
     * Check for performance issues and log warnings
     */
    checkPerformance() {
        const avgTime = this.getAverageUpdateTime();

        if (avgTime > this.criticalThreshold) {
            console.warn(`Chart performance critical: ${avgTime.toFixed(1)}ms average update time. Consider using HIGH_PERFORMANCE profile.`);
        } else if (avgTime > this.warningThreshold) {
            console.warn(`Chart performance degraded: ${avgTime.toFixed(1)}ms average update time. Consider optimizations.`);
        }
    }

    /**
     * Get performance recommendations
     */
    getRecommendations() {
        const avgTime = this.getAverageUpdateTime();
        const recommendations = [];

        if (avgTime > this.criticalThreshold) {
            recommendations.push('Switch to HIGH_PERFORMANCE profile');
            recommendations.push('Reduce maxDataPoints to 500-1000');
            recommendations.push('Increase batchUpdateInterval to 2000ms or higher');
            recommendations.push('Disable point markers (pointRadius: 0)');
        } else if (avgTime > this.warningThreshold) {
            recommendations.push('Consider BALANCED performance profile');
            recommendations.push('Enable batch updates if not already enabled');
            recommendations.push('Reduce borderWidth to 1');
        }

        return recommendations;
    }
}