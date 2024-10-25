/** @odoo-module **/
import { loadJS } from "@web/core/assets";
import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { session } from '@web/session';
const { Component,onMounted, onWillStart, useState, useEffect,useRef } = owl;
const { DateTime } = luxon;
import { renderToElement } from "@web/core/utils/render";

export class setu_rma_dashboard extends Component{
    setup() {
        super.setup();
         this.controlPanelDisplay = {
            "top-left": true,
            "top-right": true,
            "bottom-left": false,
            "bottom-right": false,
        };
        this.rpc = useService("rpc");
        this.date_range = 'week';  // possible values : 'week', 'month', year'
        this.date_from = moment.utc().subtract(1, 'week');
        this.date_to = moment.utc();
        this.ui = useState(useService("ui"));
        this.ui.block();
        this.graphs = [];
        this.chartIds = {};
        onWillStart(async () => {
            await loadJS("/web/static/lib/Chart/Chart.js");
            var self = this;
            display: { controlPanel: true }
            return self.fetch_data();
        })
         onMounted(()=> {
              this._computeControlPanelProps();
              this.render_graphs(this.chart_values);
                this.ui.unblock();
            });

      }
    async fetch_data() {
        var self = this;
        const result = await this.rpc(  '/setu_rma/fetch_dashboard_data', {
               date_from: this.date_from.year()+'-'+(this.date_from.month()+1)+'-'+this.date_from.date(),
                date_to: this.date_to.year()+'-'+(this.date_to.month()+1)+'-'+this.date_to.date(),
                company_id: session.user_companies.allowed_companies,
                date_range : this.date_range
        });
        self.chart_values = result
        return result;
    }

    _computeControlPanelProps() {
        const $searchview = $(renderToElement("setu_rma.DateRangeButtons", {
            content: this,
        }));
        $searchview.find('button.js_date_range').click((ev) => {
            $searchview.find('button.js_date_range.active').removeClass('active');
            $(ev.target).addClass('active');
            this.on_date_range_button($(ev.target).data('date'));
        });
        $('.o_control_panel_navigation').html($searchview)
    }

    render_graphs(chart_values) {
        var self = this;
        $.each(self.chart_values, function(index, chartvalue){
            var $canvasContainer = $('<div/>', {class: 'o_graph_canvas_container'});
            self.$canvas = $('<canvas/>');
            $canvasContainer.append(self.$canvas);
            $('#'+chartvalue.chart_name).append($canvasContainer);
            var ctx = self.$canvas[0];
            ctx.height = 106
            var labels = chartvalue.chart_values[0].values.map(function (value) {
                return value.name
            });
            var datasets = chartvalue.chart_values.map(function (group, index) {
                return {
                    label: group.key,
                    data: group.values.map(function (value) {
                        return value.count;
                    }),
                    labels: group.values.map(function (value) {
                        return value.name;
                    }),
                    backgroundColor: chartvalue.chart_type == 'bar'? self.getRandomRgb() : group.values.map(function (value) {
                        return self.getRandomRgb()
                    }),
                    borderWidth: 1
                };
            });
            const data = {
              labels: labels,
              datasets: datasets
            };
            const options = {
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: chartvalue.chart_title,
                            position: 'bottom',
                        }
                    }
                },
            }
            if(chartvalue.chart_type == 'bar'){
                options.scales = {
                    y: {
                        ticks: {
                            beginAtZero: true
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: chartvalue.chart_title,
                            position: 'bottom',
                        }
                    }
                }
            }
            if(chartvalue.chart_type == 'pie'){
                 options.scales = {
                    x: {
                      grid: {
                        display: false,
                      },
                      border: {
                        display: false,
                      },
                      ticks: {
                        display: false,
                      },
                    title: {
                        display: true,
                        text: chartvalue.chart_title,
                        position: 'bottom',
                    }
                    },
                    y: {
                      grid: {
                        display: false,
                      },
                      border: {
                        display: false,
                      },
                      ticks: {
                        display: false,
                      },
                    },
                }
            }
            self.chart = new Chart(ctx, {
                type: chartvalue.chart_type,
                data: data,
                 options: options
            });
        });


    }

    getRandomRgb() {
      var num = Math.round(0xffffff * Math.random());
      var r = num >> 16;
      var g = num >> 8 & 255;
      var b = num & 255;
      return 'rgb(' + r + ', ' + g + ', ' + b + ', 0.7)';
    }
    render_dashboards() {
        var self = this;
        $('.o_rma_dashboard').append(renderToElement('setu_rma.dashboard_content_qweb', {content: self}));
    }
    on_date_range_button(date_range) {
        if (date_range === 'week') {
            this.date_range = 'week';
            this.date_from = moment.utc().subtract(1, 'weeks');
        } else if (date_range === 'month') {
            this.date_range = 'month';
            this.date_from = moment.utc().subtract(1, 'months');
        } else if (date_range === 'year') {
            this.date_range = 'year';
            this.date_from = moment.utc().subtract(1, 'years');
        } else {
            console.log('Unknown date range. Choose between [week, month, year]');
            return;
        }

        var self = this;
        Promise.resolve(this.fetch_data()).then(function () {
            $('.o_rma_dashboard').empty();
            self.render_dashboards();
            self.render_graphs();
        });

    }
}
ControlPanel.defaultProps = {
        withBreadcrumbs: true,
        withSearchBar: true,
    };
setu_rma_dashboard.components = {
    ControlPanel,
};



setu_rma_dashboard.template = 'setu_rma.RmaDashboardMain';

registry.category('actions').add('rma_dashboard_client_action', setu_rma_dashboard);
