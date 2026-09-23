revoke execute on function public.is_trading_member() from anon;
revoke execute on function public.claim_trading_membership() from anon;

grant execute on function public.is_trading_member() to authenticated;
grant execute on function public.claim_trading_membership() to authenticated;
