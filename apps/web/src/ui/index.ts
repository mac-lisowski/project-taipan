// Design system barrel: app code imports visual pieces from "@/ui" only.
// Components must accept className and merge it via cn().

export { cn } from "./lib/utils";
export { Badge } from "./components/badge";
export { Button } from "./components/button";
export { CodeTabs, type CodeTab } from "./components/code-tabs";
export { Field } from "./components/field";
export { Input } from "./components/input";
export { Label } from "./components/label";
export { NewsCard } from "./components/news-card";
export { Panel, PanelHeader } from "./components/panel";
export { Sparkline } from "./components/sparkline";
export { Stat } from "./components/stat";
export { Switch } from "./components/switch";
export {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./components/select";
export {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "./components/table";
