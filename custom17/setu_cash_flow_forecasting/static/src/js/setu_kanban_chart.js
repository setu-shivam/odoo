/** @odoo-module **/

import { registry } from "@web/core/registry";
import { loadJS } from "@web/core/assets";
import { patch } from "@web/core/utils/patch";
import { JournalDashboardGraphField } from "@web/views/fields/journal_dashboard_graph/journal_dashboard_graph_field";

patch(JournalDashboardGraphField.prototype, {
    renderChart() {
         if (this.chart) {
            this.chart.destroy();
        }
        let config;
        if(this.props.graphType === 'gauge'){
            config = this._getGaugeChartConfig();
        }
        if (this.props.graphType === "line") {
            config = this.getLineChartConfig();
        } else if (this.props.graphType === "bar") {
            config = this.getBarChartConfig();
        }
        this.chart = new Chart(this.canvasRef.el, config);
    },
    _getGaugeChartConfig () {
            var data = [];
            var labels = [];
            var backgroundColor = [];
            if(this.data[0].title === "dummy"){
                this.data[0].values.forEach(function (pt) {
                    data.push(pt.value);
                    labels.push(pt.label);
                    var color = pt.type === 'past' ? '#ccbdc8' : (pt.type === 'future' ? '#a5d8d7' : '#ebebeb');
                    backgroundColor.push(color);
                });
                return {
                    type: 'doughnut',
                    data: {
                        labels: ["No Forecast Calculated"],
                        datasets: [{
                            data: data,
                            backgroundColor: backgroundColor,
                        }],
                    },
                    options: {
                         title: {
                                display: true,
                                text: 'No Forecast Calculated'
                            },
                            legend: {
                                display: false
                            },
                        maintainAspectRatio: true,
                        
                        rotation: -90,
                        circumference: 180,
                        plugins: {
                            tooltip: {
                                enabled: false
                            },
                        },
                    },
                }
            }
            else if(this.data[0].title === "zero-dummy"){
                this.data[0].values.forEach(function (pt) {
                    data.push(pt.value);
                    labels.push(pt.label);
                    var color = pt.type === 'past' ? '#ccbdc8' : (pt.type === 'future' ? '#a5d8d7' : '#ebebeb');
                    backgroundColor.push(color);
                });
                return {
                    type: 'doughnut',
                    data: {
                        labels: ["All Forested Values Are Zero"],
                        datasets: [{
                            data: data,
                            backgroundColor: backgroundColor,
                        }],
                    },
                    options: {
                          plugins: {
                                legend: {
                                    display: false
                                },
                                title: {
                                    display: true,
                                    text: 'All Forested Values Are Zero'
                                },
                                tooltip: {
                                    enabled: false
                                },
                          },
                        maintainAspectRatio: true,
                        
                        rotation: -90,
                        circumference: 180,
                    },
                }
            }
            else{
                this.data[0].values.forEach(function (pt) {
                    data.push(pt.value);
                    labels.push(pt.label);
                    var color = pt.type === 'past' ? '#ccbdc8' : (pt.type === 'future' ? '#a5d8d7' : '#ebebeb');
                    backgroundColor.push(color);
                });
                return {
                    type: 'doughnut',
                    data: {
                        labels: labels,
                        datasets: [{
                            data: data,
                            backgroundColor: backgroundColor,
                        }],
                    },
                    options: {
                        maintainAspectRatio: true,
                        
                        rotation: -90,
                        circumference: 180,
                         plugins: {
                            legend: {
                                display: false
                            },
                        },
                    },
                }
            }
        }
});

