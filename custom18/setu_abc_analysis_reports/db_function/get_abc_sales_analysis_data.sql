DROP FUNCTION IF EXISTS public.get_abc_sales_analysis_data(integer[], integer[], integer[], integer[], date, date, text);
CREATE OR REPLACE FUNCTION public.get_abc_sales_analysis_data(
    IN company_ids integer[],
    IN product_ids integer[],
    IN category_ids integer[],
    IN warehouse_ids integer[],
    IN start_date date,
    IN end_date date,
    IN abc_analysis_type text)
  RETURNS TABLE
  (
    company_id integer, company_name character varying, product_id integer, product_name character varying,
    product_category_id integer, category_name character varying, warehouse_id integer, warehouse_name character varying,
    sales_qty numeric, sales_amount numeric,total_orders numeric, sales_amount_per numeric, cum_sales_amount_per integer, analysis_category text
) AS
$BODY$
        DECLARE
            a_from INTEGER := (select value from ir_config_parameter where key = 'setu_abc_analysis_reports.setu_abc_a_from');
            a_to INTEGER := (select value from ir_config_parameter where key = 'setu_abc_analysis_reports.setu_abc_a_to');
            b_from INTEGER := (select value from ir_config_parameter where key = 'setu_abc_analysis_reports.setu_abc_b_from');
            b_to INTEGER := (select value from ir_config_parameter where key = 'setu_abc_analysis_reports.setu_abc_b_to');
            c_from INTEGER := (select value from ir_config_parameter where key = 'setu_abc_analysis_reports.setu_abc_c_from');
            c_to INTEGER := (select value from ir_config_parameter where key = 'setu_abc_analysis_reports.setu_abc_c_to');
        BEGIN
            Return Query
            --This table is used for fetch records from get_sales_data table and generate rank for records based on sales amount
            with all_data as (
                Select DENSE_RANK() over(partition by ad.warehouse_id order by ad.sales_amount desc) as rank_id,
                        ad.*
                from get_sales_data(company_ids, product_ids, category_ids, warehouse_ids, start_date, end_date)ad
            ),
            --This table is use for calculate total sales qty, sales amount and total orders warehouse wise
            warehouse_wise_abc_analysis as(
                Select
                    a.warehouse_id,
                    a.warehouse_name,
                    sum(a.sales_qty) as total_sales,
                    sum(a.sales_amount) as total_sales_amount,
                    sum(a.total_orders) as total_orders
                from all_data a
                group by a.warehouse_id, a.warehouse_name
            )
            Select final_data.* from
            (
                --This table is used for classify records into A,B,C category based on rank and user configuration
                Select
                    result.company_id, result.company_name, result.product_id, result.product_name,
                    result.product_category_id, result.category_name, result.warehouse_id, result.warehouse_name,
                    result.sales_qty, result.sales_amount,result.total_orders, result.sales_amount_per, 0 as cum_sales_amount_per,

                    case when result.rank_id <= round((result.max_ware_rank::float*(a_to::float/100::float))) then 'A'
	                when result.rank_id >=round((result.max_ware_rank::float*(b_from::float/100::float))) and result.rank_id <= round((result.max_ware_rank*(b_to::float/100::float))) then 'B'
	                else 'C'
                    end as analysis_category
                from
                (
                    select
                        max(a.rank_id) over (partition by a.warehouse_id) as max_ware_rank,a.rank_id,
                        a.company_id,a.company_name,a.product_id,a.product_name,a.product_category_id,a.category_name,a.warehouse_id,a.warehouse_name,
                        max(a.sales_qty) as sales_qty, max(a.sales_amount) as sales_amount, max(a.total_orders) as total_orders, max(a.sales_amount_per) as sales_amount_per
                    from
                        (
                            -- This table is used for set value for sales_amount_per field warehouse wise
                            Select
                                all_data.*,
                                round(case when wwabc.total_sales_amount <= 0.00 then 0 else
                                (all_data.sales_amount / wwabc.total_sales_amount * 100.0)::numeric
                                end, 2) as sales_amount_per
                            from all_data
                            Inner Join warehouse_wise_abc_analysis wwabc on all_data.warehouse_id = wwabc.warehouse_id
                        )a
                    group by a.company_id,a.rank_id,a.company_name,a.product_id,a.product_name,a.product_category_id,a.category_name,a.warehouse_id,a.warehouse_name
                )result
            )final_data
            where
            1 = case when abc_analysis_type = 'all' then 1
            else
                case when abc_analysis_type = 'high_sales' then
                    case when final_data.analysis_category = 'A' then 1 else 0 end
                else
                    case when abc_analysis_type = 'medium_sales' then
                        case when final_data.analysis_category = 'B' then 1 else 0 end
                    else
                        case when abc_analysis_type = 'low_sales' then
                            case when final_data.analysis_category = 'C' then 1 else 0 end
                        else 0 end
                    end
                end
            end
            order by final_data.warehouse_id, final_data.analysis_category;
        END; $BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100
  ROWS 1000;
