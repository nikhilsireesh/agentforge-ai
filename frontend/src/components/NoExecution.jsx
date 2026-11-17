import { Rocket } from "lucide-react";
import { Link } from "react-router-dom";
import { Button, Card, EmptyState } from "./ui";

export function NoExecution({ message = "Run the AI workflow on a project to see results here." }) {
  return (
    <Card>
      <EmptyState
        icon={Rocket}
        title="No execution selected"
        description={message}
        action={
          <Link to="/projects/new">
            <Button icon={Rocket}>Create a project</Button>
          </Link>
        }
      />
    </Card>
  );
}
