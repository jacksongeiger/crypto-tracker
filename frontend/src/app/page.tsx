import { redirect } from "next/navigation";

export default function Root() {
  redirect("/news/overview");
}
