DROP FUNCTION IF EXISTS public.get_icar_inventory_coverage_abc_analysis_data(integer[], integer[], integer[], integer[], date, date, character varying,integer, character varying, text,character varying,character varying,integer);
CREATE OR REPLACE FUNCTION public.get_icar_inventory_coverage_abc_analysis_data(
    IN company_ids integer[],
    IN product_ids integer[],
    IN category_ids integer[],
    IN warehouse_ids integer[],
    IN start_date date,
    IN end_date date,
    IN report_by character varying,
    IN wizard_id integer,
    IN include_internal_transfers character varying,
    IN abc_analysis_type text,
    IN vendor_strategy character varying,
    IN coverage_ratio_strategy character varying,
    IN static_coverage_days integer)
  RETURNS void AS
$BODY$
    DECLARE
        day_difference integer := ((end_date::Date-start_date::Date)+1);
    BEGIN
        --get Inventory coverage report data in table
        PERFORM icr_get_inventory_coverage_data(company_ids,product_ids,category_ids,warehouse_ids,start_date,end_date,report_by,wizard_id,include_internal_transfers,vendor_strategy,coverage_ratio_strategy,static_coverage_days);
        -- Update table by adding values in analysis category column from abc report function get_abc_sales_analysis_data
        UPDATE setu_inventory_coverage_analysis_bi_report
            set analysis_category = abc.analysis_category
        from (Select * from get_abc_sales_analysis_data(company_ids, product_ids, category_ids, warehouse_ids, start_date, end_date, abc_analysis_type))  abc
        where abc.product_id = setu_inventory_coverage_analysis_bi_report.product_id and abc.company_id = setu_inventory_coverage_analysis_bi_report.company_id and abc.warehouse_id = setu_inventory_coverage_analysis_bi_report.warehouse_id;
    END;
$BODY$
LANGUAGE plpgsql VOLATILE
COST 100;
