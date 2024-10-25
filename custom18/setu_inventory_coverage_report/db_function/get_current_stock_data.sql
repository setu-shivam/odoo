DROP FUNCTION IF EXISTS public.icr_get_current_stock_data(integer[], integer[], integer[], integer[], date, date);
CREATE OR REPLACE FUNCTION public.icr_get_current_stock_data(
    IN company_ids integer[],
    IN product_ids integer[],
    IN category_ids integer[],
    IN warehouse_ids integer[],
    IN start_date date,
    IN end_date date)
  RETURNS TABLE(company_id integer,product_id integer, product_category_id integer,warehouse_id integer,location_id integer,current_stock numeric) AS
$BODY$
BEGIN
    Return Query
    --Query Returns current/on hand quantity
    select
        min(sq.company_id) as company_id,
        sq.product_id,
        tmpl.categ_id as category,
        ware.id as warehouse_id,
        min(sq.location_id) as location_id,
        sum(sq.quantity) as current_stock
    from
    stock_quant sq
    Join product_product prod on prod.id = sq.product_id
    Join product_template tmpl on tmpl.id = prod.product_tmpl_id
    join stock_location sl on sl.id = sq.location_id
    left Join stock_warehouse ware ON sl.parent_path::text ~~ concat('%/', ware.view_location_id, '/%')
    Where sl.usage = 'internal' and prod.active = True and tmpl.active = True and tmpl.type != 'combo' and tmpl.is_storable
     and 1 = case when array_length(company_ids,1) >= 1 then
     	case when sq.company_id = ANY(company_ids) then 1 else 0 end
     	else 1 end
     --product dynamic condition
     and 1 = case when array_length(product_ids,1) >= 1 then
     	case when sq.product_id = ANY(product_ids) then 1 else 0 end
     	else 1 end
     --category dynamic condition
     and 1 = case when array_length(category_ids,1) >= 1 then
     	case when tmpl.categ_id = ANY(category_ids) then 1 else 0 end
     	else 1 end
     --warehouse dynamic condition
     and 1 = case when array_length(warehouse_ids,1) >= 1 then
     	case when ware.id = ANY(warehouse_ids) then 1 else 0 end
     	else 1 end
    group by sq.product_id,tmpl.categ_id,ware.id;
    END;
$BODY$
LANGUAGE plpgsql VOLATILE
COST 100
ROWS 1000;


