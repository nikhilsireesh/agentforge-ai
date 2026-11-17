import { Compass } from "lucide-react";
import { Link } from "react-router-dom";
import { Button, Card, EmptyState } from "../components/ui";

export default function NotFound() {
  return (
    <Card>
      <EmptyState icon={Compass} title="Page not found" description="The page you are looking for does not exist."
        action={<Link to="/"><Button>Back to overview</Button></Link>} />
    </Card>
  );
}
