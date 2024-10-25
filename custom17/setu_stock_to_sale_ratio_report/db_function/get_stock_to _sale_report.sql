--DROP FUNCTION public.get_product_stock_to_sale_ratio(integer[], integer[], integer[], date, date);

CREATE OR REPLACE FUNCTION public.get_product_stock_to_sale_ratio(
    IN company_ids integer[],
    IN product_ids integer[],
    IN category_ids integer[],
    IN start_date date,
    IN end_date date)
    RETURNS TABLE(
	company_id integer,company_name character varying,
	currency_id integer,currency_name character varying,
	product_id integer,product_name character varying,
	categ_id integer, product_category_name character varying,
	opening numeric,
	closing numeric,
	avg_stock_value numeric,
	sales numeric,sales_return numeric,
	net_sales numeric,
	avg_cost numeric
  ) AS

$BODY$
BEGIN

RETURN QUERY

select
	foo.company_id,	foo.company_name,
	foo.currency_id,foo.currency_name,
	foo.product_id,	foo.product_name,
	foo.categ_id,   foo.product_category_name,
	foo.opening,
	foo.closing,
	round((foo.opening+foo.closing) / 2 ,2) as avg_stock_value,
	tmp.sales,tmp.sales_return,
	tmp.net_sales as net_sales,
	foo.avg_cost
from(
select
	tmp.company_id,     tmp.company_name,
	tmp.currency_id,    tmp.currency_name,
	tmp.product_id,     tmp.product_name,
	tmp.categ_id,   	tmp.product_category_name,
	sum(tmp.opening)  AS opening,
	sum(tmp.closing) as closing,
	round(avg(tmp.avg_cost),3) as avg_cost
from (
	select
		svl.company_id,		    comp.name as company_name,
		cur.id as currency_id,	cur.name as currency_name,
		svl.product_id,
		case when prod.default_code is NULL THEN (tmpl.name ->>'en_US'::character varying)
			else ('['||prod.default_code||']'||' '||(tmpl.name ->>'en_US'))::character varying
			end as product_name,
--		('['||prod.default_code||']'||' '||(tmpl.name ->>'en_US'))::character varying as product_name,
		svl.categ_id,		    categ.complete_name as product_category_name,
		round(avg(svl.unit_cost),3) as avg_cost,
		sum(svl.value)  AS opening,
		0 as closing
	from
		stock_valuation_layer svl
		join res_company comp on svl.company_id = comp.id
		join res_currency cur on comp.currency_id = cur.id
		join product_product prod on svl.product_id = prod.id
		join product_template tmpl on prod.product_tmpl_id = tmpl.id
		join product_category categ on svl.categ_id = categ.id
	where
		svl.create_date::date < start_date::date

		and prod.active = true and tmpl.active = true
		and 1 = case when array_length(product_ids,1) >= 1 then
			case when svl.product_id = ANY(product_ids) then 1 else 0 end
				else 1 end
		and 1 = case when array_length(company_ids,1) >= 1 then
			case when svl.company_id = ANY(company_ids) then 1 else 0 end
				else 1 end
		--category dynamic condition
		and 1 = case when array_length(category_ids,1) >= 1 then
			case when tmpl.categ_id = ANY(category_ids) then 1 else 0 end
				else 1 end
	group by 1,2,3,4,5,6,7,8

	UNION all

	select
		svl.company_id,			comp.name as company_name,
		cur.id as currency_id,	cur.name as currency_name,
		svl.product_id,
		case when prod.default_code is NULL THEN (tmpl.name ->>'en_US'::character varying)
			else ('['||prod.default_code||']'||' '||(tmpl.name ->>'en_US'))::character varying
			end as product_name,
		svl.categ_id,			categ.complete_name as product_category_name,
		round(avg(svl.unit_cost),3) as avg_cost,
		0  AS opening,
		sum(svl.value) as closing
	from
		stock_valuation_layer svl
		join product_product prod on svl.product_id = prod.id
		join product_template tmpl on prod.product_tmpl_id = tmpl.id
		join product_category categ on svl.categ_id = categ.id
		join res_company comp on svl.company_id = comp.id
		join res_currency cur on comp.currency_id = cur.id
	where
		svl.create_date::date <= end_date::date

		and prod.active = true and tmpl.active = true
		and 1 = case when array_length(product_ids,1) >= 1 then
			case when svl.product_id = ANY(product_ids) then 1 else 0 end
				else 1 end
		and 1 = case when array_length(company_ids,1) >= 1 then
			case when svl.company_id = ANY(company_ids) then 1 else 0 end
				else 1 end
		--category dynamic condition
		and 1 = case when array_length(category_ids,1) >= 1 then
			case when tmpl.categ_id = ANY(category_ids) then 1 else 0 end
				else 1 end
	group by 1,2,3,4,5,6,7,8
)tmp
group by 1,2,3,4,5,6,7,8
)foo
left join (
		select tmp.company_id,tmp.product_id,abs(sum(tmp.sales))as sales,sum(tmp.sale_return)as sales_return,abs(sum(tmp.sales)+sum(tmp.sale_return)) as net_sales
from(
		select
			svl.company_id,svl.product_id,svl.value as sales,0 as sale_return
		from stock_valuation_layer svl
			join stock_move sm on svl.stock_move_id = sm.id
			join product_product prod on svl.product_id = prod.id
			join product_template tmpl on prod.product_tmpl_id = tmpl.id
		where sm.origin_returned_move_id is null
			and svl.remaining_value is null
			and sm.date::date >= start_date::date and sm.date::date <= end_date::date
			and svl.value<0

			and prod.active = true and tmpl.active = true
			and 1 = case when array_length(product_ids,1) >= 1 then
				case when svl.product_id = ANY(product_ids) then 1 else 0 end
					else 1 end
			and 1 = case when array_length(company_ids,1) >= 1 then
				case when svl.company_id = ANY(company_ids) then 1 else 0 end
					else 1 end
			--category dynamic condition
			and 1 = case when array_length(category_ids,1) >= 1 then
				case when tmpl.categ_id = ANY(category_ids) then 1 else 0 end
					else 1 end


		group by 1,2,3,4

		union all

		select
		svl.company_id,svl.product_id,0 as sales,
			svl.value as sale_return
		from stock_valuation_layer svl
			join stock_move sm on svl.stock_move_id = sm.id
			join product_product prod on svl.product_id = prod.id
			join product_template tmpl on prod.product_tmpl_id = tmpl.id
		where sm.origin_returned_move_id is not null
			and svl.remaining_value is not null
			and sm.date::date >= start_date::date and sm.date::date <= end_date::date
			and svl.value>0

			and prod.active = true and tmpl.active = true
			and 1 = case when array_length(product_ids,1) >= 1 then
				case when svl.product_id = ANY(product_ids) then 1 else 0 end
					else 1 end
			and 1 = case when array_length(company_ids,1) >= 1 then
				case when svl.company_id = ANY(company_ids) then 1 else 0 end
					else 1 end
			--category dynamic condition
			and 1 = case when array_length(category_ids,1) >= 1 then
				case when tmpl.categ_id = ANY(category_ids) then 1 else 0 end
					else 1 end

		group by 1,2,3,4
	)tmp
	group by tmp.product_id,tmp.company_id

)tmp on tmp.product_id = foo.product_id and tmp.company_id =foo.company_id;


END; $BODY$
LANGUAGE plpgsql VOLATILE
COST 100
ROWS 1000;
