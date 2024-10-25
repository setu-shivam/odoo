DROP FUNCTION IF EXISTS public.get_inventory_xyz_analysis_data(integer[], integer[], integer[], text);
CREATE OR REPLACE FUNCTION public.get_inventory_xyz_analysis_data(
IN company_ids integer[],
IN product_ids integer[],
IN category_ids integer[],
IN inventory_analysis_type text)
RETURNS TABLE(company_id integer, company_name character varying, product_id integer, product_name character varying, product_category_id integer, category_name character varying, current_stock numeric, stock_value numeric, stock_value_per numeric, cum_stock_value_per numeric, analysis_category text) AS
$BODY$
            DECLARE
                x_from INTEGER := (select value from ir_config_parameter where key = 'setu_abc_analysis_reports.setu_xyz_x_from');
                x_to INTEGER := (select value from ir_config_parameter where key = 'setu_abc_analysis_reports.setu_xyz_x_to');
                y_from INTEGER := (select value from ir_config_parameter where key = 'setu_abc_analysis_reports.setu_xyz_y_from');
                y_to INTEGER := (select value from ir_config_parameter where key = 'setu_abc_analysis_reports.setu_xyz_y_to');
                z_from INTEGER := (select value from ir_config_parameter where key = 'setu_abc_analysis_reports.setu_xyz_z_from');
                z_to INTEGER := (select value from ir_config_parameter where key = 'setu_abc_analysis_reports.setu_xyz_z_to');
            BEGIN
                Return Query
                --This table is used for generate rank for records based on stock value
                with all_data as (
                Select DENSE_RANK() over(partition by ad.company_id order by ad.stock_value desc) as rank_id,
                        ad.*
                from
                    (Select
                        layer.company_id,
                        cmp.name as company_name,
                        layer.product_id,
                        case when prod.default_code is null then (tmpl.name ->>'en_US')::character varying
                        else
							('['||prod.default_code||']'||' '||(tmpl.name ->>'en_US'))::character varying
						end as product_name,
                        tmpl.categ_id as product_category_id,
                        cat.complete_name as category_name,
                        sum(quantity) as current_stock,
                        sum(value) as stock_value
                    from
                        stock_valuation_layer layer
                            Inner Join res_company cmp on cmp.id = layer.company_id
                            Inner Join product_product prod on prod.id = layer.product_id
                            Inner Join product_template tmpl on tmpl.id = prod.product_tmpl_id
                            Inner Join product_category cat on cat.id = tmpl.categ_id
                    Where prod.active = True and tmpl.active = True and tmpl.is_storable = True
                        --company dynamic condition
                        and 1 = case when array_length(company_ids,1) >= 1 then
                            case when layer.company_id = ANY(company_ids) then 1 else 0 end
                            else 1 end
                        --product dynamic condition
                        and 1 = case when array_length(product_ids,1) >= 1 then
                            case when layer.product_id = ANY(product_ids) then 1 else 0 end
                            else 1 end
                        --category dynamic condition
                        and 1 = case when array_length(category_ids,1) >= 1 then
                            case when tmpl.categ_id = ANY(category_ids) then 1 else 0 end
                            else 1 end
                   group by layer.company_id, cmp.name, layer.product_id,prod.default_code,tmpl.name,tmpl.categ_id, cat.complete_name)ad
                ),
                --This table is use for calculate total current stock and stock value warehouse wise
                warehouse_wise_xyz_analysis as(
                    Select a.company_id, a.company_name, sum(a.current_stock) as total_current_stock, sum(a.stock_value) as total_stock_value
                    from all_data a
                    group by a.company_id, a.company_name
                )
                Select final_data.* from
                (
                     --This table is used for classify records into X,Y,Z category based on rank and user configuration
                    Select
                        result.company_id, result.company_name, result.product_id, result.product_name,
                        result.product_category_id, result.category_name, result.current_stock, result.stock_value,result.warehouse_stock_value_per,
                        0::numeric as cum_stock_value_per,
                        case when result.rank_id <= round((result.max_ware_rank::float*(x_to::float/100::float))) then 'X'
                        when result.rank_id >=round((result.max_ware_rank::float*(y_from::float/100::float))) and result.rank_id <= round((result.max_ware_rank*(y_to::float/100::float))) then 'Y'
                        else 'Z'
                        end as analysis_category
                    from
                    (
                        select
                            max(a.rank_id) over (partition by a.company_id) as max_ware_rank,a.rank_id,
                            a.company_id,a.company_name,a.product_id,a.product_name,a.product_category_id,a.category_name,
                            max(a.current_stock) as current_stock, max(a.stock_value) as stock_value, max(a.warehouse_stock_value_per) as warehouse_stock_value_per
                        from
                        (
                            -- This table is used for set value for stock_value_per field warehouse wise
                            Select
                                all_data.*,
                                case when wwxyz.total_stock_value <= 0.00 then 0 else
                                    Round((all_data.stock_value / wwxyz.total_stock_value * 100.0)::numeric,2)
                                end as warehouse_stock_value_per
                            from all_data
                                Inner Join warehouse_wise_xyz_analysis wwxyz on all_data.company_id = wwxyz.company_id
                        )a
                        group by a.company_id,a.rank_id,a.company_name,a.product_id,a.product_name,a.product_category_id,a.category_name
                    )result
                )final_data
                where
                1 = case when inventory_analysis_type = 'all' then 1
                else
                    case when inventory_analysis_type = 'high_stock' then
                        case when final_data.analysis_category = 'X' then 1 else 0 end
                    else
                        case when inventory_analysis_type = 'medium_stock' then
                            case when final_data.analysis_category = 'Y' then 1 else 0 end
                        else
                            case when inventory_analysis_type = 'low_stock' then
                                case when final_data.analysis_category = 'Z' then 1 else 0 end
                            else 0 end
                        end
                    end
                end
                order by final_data.company_id, final_data.stock_value desc;

            END; $BODY$
LANGUAGE plpgsql VOLATILE
COST 100
ROWS 1000;
