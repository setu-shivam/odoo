DROP FUNCTION IF EXISTS public.icr_get_inventory_coverage_data(integer[], integer[], integer[], integer[], date, date, character varying,integer,character varying,character varying,character varying,integer);
CREATE OR REPLACE FUNCTION public.icr_get_inventory_coverage_data(
    IN company_ids integer[],
    IN product_ids integer[],
    IN category_ids integer[],
    IN warehouse_ids integer[],
    IN start_date date,
    IN end_date date,
    IN report_by character varying,
    IN wizard_id integer,
    IN include_internal_transfers character varying,
    IN vendor_strategy character varying,
    IN coverage_ratio_strategy character varying,
    IN static_coverage_days integer)
--  RETURNS TABLE(company_id integer,product_id integer, product_tmpl_id integer, product_category_id integer,warehouse_id integer,current_stock numeric,ads numeric,coverage_days numeric,
--                partner_id integer, currency_id integer, price numeric, delay integer, min_qty numeric, price_in_currency numeric) AS
RETURNS void AS
$BODY$
    DECLARE
        day_difference integer := ((end_date::Date-start_date::Date)+1);
        static_coverage_days integer := (case when static_coverage_days <= 0 then 1 else static_coverage_days end);
    BEGIN
        DELETE FROM setu_inventory_coverage_analysis_bi_report;
        IF vendor_strategy = 'cheapest' then
            Insert into setu_inventory_coverage_analysis_bi_report(company_id,company_name,product_id,product_name,product_category_id,category_name,warehouse_id,warehouse_name,product_tmpl_id,current_stock,average_daily_sales,coverage_days,wizard_id,
                                                                    partner_id, currency_id, price, delay, min_qty, price_in_currency, coverage_ratio, out_stock_days, sold_qty)
            select
                data.company_id,data.company_name,data.product_id,data.product_name,data.product_category_id,data.category_name,data.warehouse_id,data.warehouse_name,data.product_tmpl_id,
                data.current_stock,data.ads,data.coverage_days, data.wizard_id, ch.partner_id, ch.currency_id, ch.price, ch.delay, ch.min_qty, ch.price_in_currency,
                case when coverage_ratio_strategy = 'static_days' then ((data.coverage_days / static_coverage_days)*100) else ((data.coverage_days / greatest(coalesce(ch.delay, 1), 1))*100) end as coverage_ratio,
                case when data.coverage_days <= 0 then 0
                     when coverage_ratio_strategy = 'static_days' and (static_coverage_days - data.coverage_days) > 0
                            then (static_coverage_days - data.coverage_days)
                     when (coverage_ratio_strategy = 'static_days' and (static_coverage_days - data.coverage_days) <= 0) or
                            (coverage_ratio_strategy != 'static_days' and (coalesce(ch.delay, 1) - data.coverage_days) <= 0)
                            then 0
                     when coverage_ratio_strategy != 'static_days' and (coalesce(ch.delay, 1) - data.coverage_days) > 0
                            then (coalesce(ch.delay, 1) - data.coverage_days)
                end as out_stock_days,
                data.sold_qty
            from
            (select
                cov.company_id,
                cov.company_name,
                cov.product_id,
                cov.product_name,
                cov.product_category_id,
                cov.category_name,
                case when report_by='warehouse' then cov.warehouse_id
                else 1 end as warehouse_id,
                case when report_by='warehouse' then cov.warehouse_name
                else 'company' end as warehouse_name,
                cov.product_tmpl_id,
                sum(cov.current_stock) as current_stock,
                case when sum(cov.sales) > 0 then round(sum(cov.sales) /day_difference,2)
                else 0 end as ads,
                case when sum(cov.sales) > 0 and sum(cov.current_stock) > 0 and round(sum(cov.sales) /day_difference,2) > 0 then round(sum(cov.current_stock)/round(sum(cov.sales) /day_difference,2))
                else 0 end as coverage_days,
                wizard_id,
                sum(cov.sales) as sold_qty
            from
                (
                select S.company_id,cmp.name as company_name, S.product_id,
                 case when prod.default_code is not null then
                ('['||prod.default_code||']'||' '||(tmpl.name ->>'en_US'))::character varying
                else (tmpl.name ->>'en_US')::character varying end as product_name,
                 S.product_category_id,cat.complete_name as category_name,S.warehouse_id,ware.name as warehouse_name, tmpl.id as product_tmpl_id, sum(S.current_stock) as current_stock,0 as sales

                    from icr_get_current_stock_data(company_ids, product_ids, category_ids, warehouse_ids, start_date, end_date)S
                    Inner Join res_company cmp on cmp.id = S.company_id
                    Inner Join product_product prod on prod.id = S.product_id
                    Inner Join product_template tmpl on tmpl.id = prod.product_tmpl_id
                    Inner Join product_category cat on cat.id = tmpl.categ_id
                    Inner Join stock_warehouse ware on ware.id = S.warehouse_id
                    group by 1,2,3,4,5,6,7,8,9

                union all
                select T.company_id,T.company_name,T.product_id,T.product_name,T.product_category_id,T.category_name,T.warehouse_id,T.warehouse_name, T.product_tmpl_id, 0 as current_stock,T.sales_qty as sales
                    from icr_get_sales_production_transaction_data(company_ids, product_ids, category_ids, warehouse_ids, start_date, end_date,include_internal_transfers)T
                )cov

                group by 1,2,3,4,5,6,7,8,9)data
                left join (select
                            *
                       from (
                            select
                                row_number() over(partition by pa.product_tmpl_id,pa.company_id order by pa.price_in_currency,pa.sequence asc) row_id,
                                pa.partner_id,
                                pa.product_id,
                                pa.product_tmpl_id,
                                pa.company_id,
                                pa.currency_id,
                                pa.sequence,
                                pa.delay,
                                pa.price,
                                pa.min_qty,
                                pa.price_in_currency
                            from
                                (select *,
                                 round(ps.price/COALESCE((SELECT
                            COALESCE((SELECT r.rate FROM res_currency_rate r
                                  WHERE r.currency_id = c.id AND r.name <= CURRENT_DATE
                                    AND (r.company_id IS NULL OR r.company_id = ps.company_id)
                               ORDER BY r.company_id, r.name DESC
                                  LIMIT 1), 1.0) AS rate
                            FROM res_currency c
                            WHERE c.id IN (ps.currency_id)),1),2) as price_in_currency
                            from product_supplierinfo ps)pa
                            )a
                            where row_id=1)ch
                       on ch.product_tmpl_id = data.product_tmpl_id and ch.company_id = data.company_id;
        else
            Insert into setu_inventory_coverage_analysis_bi_report(company_id,company_name,product_id,product_name,product_category_id,category_name,warehouse_id,warehouse_name,product_tmpl_id,current_stock,average_daily_sales,coverage_days,wizard_id,
                                                                   partner_id, currency_id, price, delay, min_qty, price_in_currency, coverage_ratio, out_stock_days, sold_qty)

            select
                data.company_id,data.company_name,data.product_id,data.product_name,data.product_category_id,data.category_name,data.warehouse_id,data.warehouse_name,data.product_tmpl_id,
                data.current_stock,data.ads,data.coverage_days, data.wizard_id, ch.partner_id, ch.currency_id, ch.price, ch.delay, ch.min_qty, ch.price_in_currency,
                case when coverage_ratio_strategy = 'static_days' then ((data.coverage_days / static_coverage_days)*100) else ((data.coverage_days / greatest(coalesce(ch.delay, 1), 1))*100) end as coverage_ratio,
                case when data.coverage_days <= 0 then 0
                     when coverage_ratio_strategy = 'static_days' and (static_coverage_days - data.coverage_days) > 0
                            then (static_coverage_days - data.coverage_days)
                     when (coverage_ratio_strategy = 'static_days' and (static_coverage_days - data.coverage_days) <= 0) or
                            (coverage_ratio_strategy != 'static_days' and (coalesce(ch.delay, 1) - data.coverage_days) <= 0)
                            then 0
                     when coverage_ratio_strategy != 'static_days' and (coalesce(ch.delay, 1) - data.coverage_days) > 0
                            then (coalesce(ch.delay, 1) - data.coverage_days)
                end as out_stock_days,
                data.sold_qty
            from
            (select
                cov.company_id,
                cov.company_name,
                cov.product_id,
                cov.product_name,
                cov.product_category_id,
                cov.category_name,
                case when report_by='warehouse' then cov.warehouse_id
                else 1 end as warehouse_id,
                case when report_by='warehouse' then cov.warehouse_name
                else 'company' end as warehouse_name,
                cov.product_tmpl_id,
                sum(cov.current_stock) as current_stock,
                case when sum(cov.sales) > 0 then round(sum(cov.sales) /day_difference,2)
                else 0 end as ads,
                case when sum(cov.sales) > 0 and sum(cov.current_stock) > 0 and round(sum(cov.sales) /day_difference,2) > 0 then round(sum(cov.current_stock)/round(sum(cov.sales) /day_difference,2))
                else 0 end as coverage_days,
                wizard_id,
                sum(cov.sales) as sold_qty
            from
                (
                select S.company_id,cmp.name as company_name, S.product_id,
                 case when prod.default_code is not null then
                ('['||prod.default_code||']'||' '||(tmpl.name ->>'en_US'))::character varying
                else (tmpl.name ->>'en_US')::character varying end as product_name,
                 S.product_category_id,cat.complete_name as category_name,S.warehouse_id,ware.name as warehouse_name, tmpl.id as product_tmpl_id, sum(S.current_stock) as current_stock,0 as sales

                    from icr_get_current_stock_data(company_ids, product_ids, category_ids, warehouse_ids, start_date, end_date)S
                    Inner Join res_company cmp on cmp.id = S.company_id
                    Inner Join product_product prod on prod.id = S.product_id
                    Inner Join product_template tmpl on tmpl.id = prod.product_tmpl_id
                    Inner Join product_category cat on cat.id = tmpl.categ_id
                    Inner Join stock_warehouse ware on ware.id = S.warehouse_id
                    group by 1,2,3,4,5,6,7,8,9

                union all
                select T.company_id,T.company_name,T.product_id,T.product_name,T.product_category_id,T.category_name,T.warehouse_id,T.warehouse_name, T.product_tmpl_id, 0 as current_stock,T.sales_qty as sales
                    from icr_get_sales_production_transaction_data(company_ids, product_ids, category_ids, warehouse_ids, start_date, end_date,include_internal_transfers)T
                )cov

                group by 1,2,3,4,5,6,7,8,9)data
                left join (select
                            *
                       from (
                            select
                                row_number() over(partition by pa.product_tmpl_id,pa.company_id order by pa.delay,pa.sequence asc) row_id,
                                pa.partner_id,
                                pa.product_id,
                                pa.product_tmpl_id,
                                pa.company_id,
                                pa.currency_id,
                                pa.sequence,
                                pa.delay,
                                pa.price,
                                pa.min_qty,
                                pa.price_in_currency
                            from
                                (select *,
                                 round(ps.price/COALESCE((SELECT
                            COALESCE((SELECT r.rate FROM res_currency_rate r
                                  WHERE r.currency_id = c.id AND r.name <= CURRENT_DATE
                                    AND (r.company_id IS NULL OR r.company_id = ps.company_id)
                               ORDER BY r.company_id, r.name DESC
                                  LIMIT 1), 1.0) AS rate
                            FROM res_currency c
                            WHERE c.id IN (ps.currency_id)),1),2) as price_in_currency
                            from product_supplierinfo ps)pa
                            )a
                            where row_id=1)ch
                       on ch.product_tmpl_id = data.product_tmpl_id and ch.company_id = data.company_id;
        END IF;

    END;
$BODY$
LANGUAGE plpgsql VOLATILE
COST 100;
