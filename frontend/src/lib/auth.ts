import "server-only";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

export async function requireTradingMember() {
  const supabase = await createClient();
  const { data, error } = await supabase.auth.getUser();
  if (error || !data.user) redirect("/login");

  const { data: membership, error: membershipError } = await supabase
    .from("trading_members")
    .select("email, display_name, role")
    .eq("user_id", data.user.id)
    .eq("active", true)
    .maybeSingle();

  if (membershipError || !membership) redirect("/access-pending");
  return { supabase, user: data.user, membership };
}
