DROP FUNCTION IF EXISTS public.icr_get_sales_production_transaction_data(integer[], integer[], integer[], integer[], date, date, character varying);
CREATE OR REPLACE FUNCTION public.icr_get_sales_production_transaction_data(
IN company_ids integer[],
IN product_ids integer[],
IN category_ids integer[],
IN warehouse_ids integer[],
IN start_date date,
IN end_date date,
IN include_internal_transfers character varying)
RETURNS TABLE(
    company_id integer, company_name character varying,
    product_id integer, product_name character varying,
    product_category_id integer, category_name character varying,
    warehouse_id integer, warehouse_name character varying,
    product_tmpl_id integer, sales_qty numeric
) AS
$BODY$
BEGIN
	Drop Table if exists sales_production_transaction_table;
	--Create temporary table to prepare data
        CREATE TEMPORARY TABLE sales_production_transaction_table(
            company_id INT,
            company_name character varying,
            product_id INT,
            product_name character varying,
            product_category_id INT,
            category_name character varying,
            warehouse_id INT,
            warehouse_name character varying,
            product_tmpl_id INT,
           	sales_qty numeric
        );
		 Insert into sales_production_transaction_table
		 --Return sales data
		 select
		 		T.company_id, T.company_name,T.product_id,
		 		T.product_name,T.product_category_id,T.category_name,
				T.warehouse_id,T.warehouse_name,T.product_tmpl_id,T.product_qty
		 from icr_get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'sales' ,start_date, end_date)T;
		 Insert into sales_production_transaction_table
		 --Return data of sales return
		 select
				T.company_id, T.company_name,T.product_id,
				T.product_name,T.product_category_id, T.category_name,
				T.warehouse_id, T.warehouse_name,T.product_tmpl_id,T.product_qty * -1
		from icr_get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'sales_return' ,start_date, end_date)T;
		Insert into sales_production_transaction_table
		--Return production out data
		select
			T.company_id, T.company_name,T.product_id,
			T.product_name,T.product_category_id,T.category_name,
			T.warehouse_id, T.warehouse_name,T.product_tmpl_id,T.product_qty
		from icr_get_stock_data(company_ids, product_ids, category_ids, warehouse_ids,'production_out' ,start_date, end_date)T;
		If include_internal_transfers = 'Y' then
			Insert into sales_production_transaction_table
			--Return internal transfer out data
			select
				T.company_id,T.company_name,T.product_id,
				T.product_name,T.product_category_id ,T.category_name,
				T.warehouse_id , T.warehouse_name,T.product_tmpl_id,T.product_qty
			from icr_get_stock_data(company_ids, product_ids, category_ids, warehouse_ids,'internal_out' ,start_date, end_date)T;
			Insert into sales_production_transaction_table
			--Return internal transfer in data
			select
				T.company_id , T.company_name,T.product_id,
				T.product_name,T.product_category_id,T.category_name,
				T.warehouse_id , T.warehouse_name,T.product_tmpl_id,T.product_qty* -1
			from icr_get_stock_data(company_ids, product_ids, category_ids, warehouse_ids,'internal_in' ,start_date, end_date)T;
		END IF;
		Return Query
		--Return prepared temporary table as Return data
		Select
        	sale.company_id,sale.company_name,sale.product_id,
			sale.product_name,sale.product_category_id,sale.category_name,
			sale.warehouse_id,sale.warehouse_name,sale.product_tmpl_id,sum(sale.sales_qty) as sales_qty
		from sales_production_transaction_table sale
		group by sale.company_id, sale.company_name, sale.product_id, sale.product_name, sale.product_category_id, sale.category_name, sale.warehouse_id, sale.warehouse_name,sale.product_tmpl_id;

	END;
$BODY$
LANGUAGE plpgsql VOLATILE
COST 100
ROWS 1000;
