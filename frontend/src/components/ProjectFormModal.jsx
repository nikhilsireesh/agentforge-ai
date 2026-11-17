import { useEffect, useState } from "react";
import { Api, errorMessage } from "../services/api";
import { Button, ErrorBanner, Field, Modal, inputClass } from "./ui";

const FIELDS = ["name", "description", "business_domain", "preferred_tech_stack", "complexity", "constraints"];

/** Edit an existing project's details. */
export function ProjectFormModal({ project, open, onClose, onSaved }) {
  const [form, setForm] = useState({});
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (project) setForm(Object.fromEntries(FIELDS.map((f) => [f, project[f] ?? ""])));
    setError(null);
  }, [project]);

  const set = (key) => (event) => setForm({ ...form, [key]: event.target.value });

  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      const body = Object.fromEntries(Object.entries(form).map(([k, v]) => [k, v === "" ? null : v]));
      if (!body.name) throw new Error("Project name is required.");
      await Api.updateProject(project.id, body);
      onSaved?.();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal open={open} title="Edit project" onClose={onClose} wide
      footer={<><Button variant="secondary" onClick={onClose}>Cancel</Button><Button loading={busy} onClick={save}>Save changes</Button></>}>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="sm:col-span-2"><Field label="Name" required><input className={inputClass} value={form.name || ""} onChange={set("name")} /></Field></div>
        <div className="sm:col-span-2"><Field label="Description"><textarea rows={3} className={inputClass} value={form.description || ""} onChange={set("description")} /></Field></div>
        <Field label="Business domain"><input className={inputClass} value={form.business_domain || ""} onChange={set("business_domain")} /></Field>
        <Field label="Complexity">
          <select className={inputClass} value={form.complexity || ""} onChange={set("complexity")}>
            <option value="">Not specified</option><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option>
          </select>
        </Field>
        <div className="sm:col-span-2"><Field label="Preferred technology stack"><input className={inputClass} value={form.preferred_tech_stack || ""} onChange={set("preferred_tech_stack")} /></Field></div>
        <div className="sm:col-span-2"><Field label="Constraints"><textarea rows={2} className={inputClass} value={form.constraints || ""} onChange={set("constraints")} /></Field></div>
      </div>
      <ErrorBanner error={error} className="mt-4" />
    </Modal>
  );
}
