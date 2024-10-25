DROP FUNCTION IF EXISTS public.get_sales_frequency_data(integer[], integer[], integer[], integer[], date, date);
CREATE OR REPLACE FUNCTION public.get_sales_frequency_data(
    IN company_ids integer[],
    IN product_ids integer[],
    IN category_ids integer[],
    IN warehouse_ids integer[],
    IN start_date date,
    IN end_date date)
  RETURNS TABLE(company_id integer, company_name character varying, product_id integer, product_name character varying, product_category_id integer, category_name character varying, warehouse_id integer, warehouse_name character varying, sales_qty numeric, total_orders bigint) AS
$BODY$
        DECLARE
            pos_id integer:= (select id from ir_module_module where name='point_of_sale' and state='installed');
            pos_installed char := (case when pos_id is not null and pos_id > 0 then 'Y' else 'N' end);
        BEGIN
        IF pos_installed = 'N' then
            Return Query
            --This table is used for count total orders and calculate total_sales from sale order line
            Select
                cmp_id, cmp_name, p_id, prod_name, categ_id, cat_name, wh_id, ware_name, sum(T.sales_qty) as total_sales,
                count(distinct T.order_id) as total_orders
            From
            (
                SELECT
                    foo.cmp_id,
                    foo.cmp_name,
                    foo.p_id,
                    foo.prod_name,
                    foo.categ_id,
                    foo.cat_name,
                    foo.wh_id,
                    foo.ware_name,
                    foo.sales_qty,
                    foo.order_id
                FROM
                (
                    SELECT
                        so.company_id as cmp_id,
                        cmp.name as cmp_name,
                        sol.product_id as p_id,
                        case when pro.default_code is null then (pt.name ->>'en_US')::character varying
                        else
							('['||pro.default_code||']'||' '||(pt.name ->>'en_US'))::character varying
						end as prod_name,
                        pt.categ_id,
                        cat.complete_name as cat_name,
                        so.warehouse_id as wh_id,
                        ware.name as ware_name,
                        sol.order_id,
                        sum(Round(sol.product_uom_qty / u.factor * u2.factor,2)) AS sales_qty
                    FROM sale_order_line sol
                        JOIN sale_order so ON sol.order_id = so.id
                        Inner Join product_product pro ON sol.product_id = pro.id
                        Inner Join product_template pt ON pro.product_tmpl_id = pt.id
                        Inner Join uom_uom u ON u.id = sol.product_uom
                        Inner Join uom_uom u2 ON u2.id = pt.uom_id
                        Inner Join res_company cmp on cmp.id = so.company_id
                        Inner Join stock_warehouse ware on ware.id = so.warehouse_id
                        Inner Join product_category cat on cat.id = pt.categ_id
                    WHERE so.state::text = ANY (ARRAY['sale'::character varying::text, 'done'::character varying::text])
                    and so.date_order::date >= start_date and so.date_order::date <= end_date and pt.type != 'combo'
                    --company dynamic condition
                    and 1 = case when array_length(company_ids,1) >= 1 then
                        case when so.company_id = ANY(company_ids) then 1 else 0 end
                        else 1 end
                    --product dynamic condition
                    and 1 = case when array_length(product_ids,1) >= 1 then
                        case when sol.product_id = ANY(product_ids) then 1 else 0 end
                        else 1 end
                    --category dynamic condition
                    and 1 = case when array_length(category_ids,1) >= 1 then
                        case when pt.categ_id = ANY(category_ids) then 1 else 0 end
                        else 1 end
                    --warehouse dynamic condition
                    and 1 = case when array_length(warehouse_ids,1) >= 1 then
                        case when so.warehouse_id = ANY(warehouse_ids) then 1 else 0 end
                        else 1 end
                    group by so.company_id, cmp.name, sol.product_id, pro.default_code,pt.name, pt.categ_id, cat.complete_name, so.warehouse_id, ware.name, sol.order_id
                ) foo
            )T
            group by cmp_id, cmp_name, p_id, prod_name, categ_id, cat_name, wh_id, ware_name;

        ELSE
            Return Query
            --This Table fetch records from sale order line and pos order lines and return combined records
            Select
                cmp_id, cmp_name, p_id, prod_name, categ_id, cat_name, wh_id, ware_name, sum(T.sales_qty) as total_sales,
                 count(distinct T.order_id) + count(distinct T.pso_id) as total_orders
            From
            (
                SELECT
                    foo.cmp_id,
                    foo.cmp_name,
                    foo.p_id,
                    foo.prod_name,
                    foo.categ_id,
                    foo.cat_name,
                    foo.wh_id,
                    foo.ware_name,
                    foo.sales_qty,
                    foo.order_id,
                    foo.pso_id
                FROM
                (
                     --This table is used for fetch records from sale order lines based on user inputs.
                    SELECT
                        so.company_id as cmp_id,
                        cmp.name as cmp_name,
                        sol.product_id as p_id,
                        case when pro.default_code is null then (pt.name ->>'en_US')::character varying
                        else
							('['||pro.default_code||']'||' '||(pt.name ->>'en_US'))::character varying
						end as prod_name,
                        pt.categ_id,
                        cat.complete_name as cat_name,
                        so.warehouse_id as wh_id,
                        ware.name as ware_name,
                        sol.order_id,
                        sum(Round(sol.product_uom_qty / u.factor * u2.factor,2)) AS sales_qty,
                        null::integer as pso_id
                    FROM sale_order_line sol
                        JOIN sale_order so ON sol.order_id = so.id
                        Inner Join product_product pro ON sol.product_id = pro.id
                        Inner Join product_template pt ON pro.product_tmpl_id = pt.id
                        Inner Join uom_uom u ON u.id = sol.product_uom
                        Inner Join uom_uom u2 ON u2.id = pt.uom_id
                        Inner Join res_company cmp on cmp.id = so.company_id
                        Inner Join stock_warehouse ware on ware.id = so.warehouse_id
                        Inner Join product_category cat on cat.id = pt.categ_id
                    WHERE so.state::text = ANY (ARRAY['sale'::character varying::text, 'done'::character varying::text])
                    and so.date_order::date >= start_date and so.date_order::date <= end_date and pt.type != 'combo'
                    --company dynamic condition
                    and 1 = case when array_length(company_ids,1) >= 1 then
                        case when so.company_id = ANY(company_ids) then 1 else 0 end
                        else 1 end
                    --product dynamic condition
                    and 1 = case when array_length(product_ids,1) >= 1 then
                        case when sol.product_id = ANY(product_ids) then 1 else 0 end
                        else 1 end
                    --category dynamic condition
                    and 1 = case when array_length(category_ids,1) >= 1 then
                        case when pt.categ_id = ANY(category_ids) then 1 else 0 end
                        else 1 end
                    --warehouse dynamic condition
                    and 1 = case when array_length(warehouse_ids,1) >= 1 then
                        case when so.warehouse_id = ANY(warehouse_ids) then 1 else 0 end
                        else 1 end
                    group by so.company_id, cmp.name, sol.product_id, pro.default_code,pt.name, pt.categ_id, cat.complete_name, so.warehouse_id, ware.name, sol.order_id

                UNION ALL

                    select
                        pso.company_id as cmp_id,
                        cmp.name as cmp_name,
                        pol.product_id as p_id,
                        case when pro.default_code is null then (tmpl.name ->>'en_US')::character varying
                        else
							('['||pro.default_code||']'||' '||(tmpl.name ->>'en_US'))::character varying
						end as prod_name,
                        tmpl.categ_id,
                        cat.complete_name as cat_name,
                        spt.warehouse_id as wh_id,
                        ware.name as ware_name,
                        null::integer as order_id,
                        sum(Round(pol.qty / u.factor * u2.factor,2)) AS sales_qty,
                        pso.id as pso_id

                    from pos_order_line pol
                            left join pos_order pso on pso.id = pol.order_id
                            left Join res_company cmp on cmp.id = pso.company_id
                            left join pos_session ps on ps.id = pso.session_id
                            left join pos_config pc on pc.id = ps.config_id
                            left join stock_picking_type spt on spt.id = pc.picking_type_id
                            left Join stock_warehouse ware on ware.id = spt.warehouse_id
                            left Join product_product pro ON pol.product_id = pro.id
                            left Join product_template tmpl ON pro.product_tmpl_id = tmpl.id
                            left join account_tax_pos_order_line_rel tax_rel on pos_order_line_id = pol.id
                            left join account_tax tax on tax.id = account_tax_id
                            left Join product_category cat on cat.id = tmpl.categ_id
                            left Join uom_uom u ON u.id = tmpl.uom_id
                            left Join uom_uom u2 ON u2.id = tmpl.uom_id

                    WHERE pso.state::text = ANY (ARRAY['paid'::character varying::text, 'invoiced'::character varying::text, 'done'::character varying::text])
                    and pso.name not ilike '%refund%'
                    and pso.date_order::date >= start_date and pso.date_order::date <= end_date and tmpl.type != 'combo'
                    --company dynamic condition
                    and 1 = case when array_length(company_ids,1) >= 1 then
                        case when pso.company_id = ANY(company_ids) then 1 else 0 end
                        else 1 end
                    --product dynamic condition
                    and 1 = case when array_length(product_ids,1) >= 1 then
                        case when pol.product_id = ANY(product_ids) then 1 else 0 end
                        else 1 end
                    --category dynamic condition
                    and 1 = case when array_length(category_ids,1) >= 1 then
                        case when tmpl.categ_id = ANY(category_ids) then 1 else 0 end
                        else 1 end
                    --warehouse dynamic condition
                    and 1 = case when array_length(warehouse_ids,1) >= 1 then
                        case when spt.warehouse_id = ANY(warehouse_ids) then 1 else 0 end
                        else 1 end
                    group by pso.company_id, cmp.name, pol.product_id, pro.default_code,pt.name, tmpl.categ_id, cat.complete_name, spt.warehouse_id, ware.name, pso.id
                ) foo
            )T
            group by cmp_id, cmp_name, p_id, prod_name, categ_id, cat_name, wh_id, ware_name;
        END IF;
        END;
        $BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100
  ROWS 1000;
