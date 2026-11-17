import { ArrowLeft, ArrowRight, Check, Rocket, Sparkles } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Card, ErrorBanner, Field, KeyValue, Notice, cx, inputClass } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { useExecutions } from "../context/ExecutionContext";
import { Api, errorMessage } from "../services/api";

const EXAMPLES = {
  leave: {
    label: "Employee Leave Management",
    name: "Employee Leave Management System",
    description: "Web application to manage employee leave, approvals and attendance for a mid-sized company.",
    business_domain: "Human Resources",
    complexity: "medium",
    preferred_tech_stack: "Python FastAPI backend, React frontend, PostgreSQL",
    constraints: "Must run on the company's internal network.\nDeliver an MVP within four weeks.",
    requirement:
      "Build an employee leave management application with employee registration, login, leave applications, manager approvals, HR administration, leave balance tracking, and attendance reports.",
  },
  inventory: {
    label: "Inventory Management",
    name: "Inventory Management System",
    description: "Track products, suppliers and stock across warehouses for a small retail business.",
    business_domain: "Retail",
    complexity: "medium",
    preferred_tech_stack: "",
    constraints: "Budget-conscious: prefer open-source components.",
    requirement:
      "Build an inventory management application with product catalogue, supplier management, warehouse stock levels, purchase orders, low-stock alerts, and inventory reports.",
  },
};

const STEPS = ["Project basics", "Business requirement", "Preferences", "Review & launch"];
const EMPTY = { name: "", description: "", business_domain: "", requirement: "", preferred_tech_stack: "", complexity: "", constraints: "" };

export default function NewProject() {
  const navigate = useNavigate();
  const { system } = useAuth();
  const { refresh } = useExecutions();
  const [step, setStep] = useState(0);
  const [form, setForm] = useState(EMPTY);
  const [startNow, setStartNow] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const set = (key) => (event) => setForm({ ...form, [key]: event.target.value });
  const loadExample = (key) => {
    const { label: _label, ...values } = EXAMPLES[key];
    setForm(values);
  };

  const stepValid = [
    form.name.trim().length > 0,
    form.requirement.trim().length >= 10,
    true,
    true,
  ];

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      const body = Object.fromEntries(Object.entries(form).map(([k, v]) => [k, v.trim() === "" ? null : v.trim()]));
      const project = await Api.createProject(body);
      if (startNow) {
        const execution = await Api.execute(project.id);
        await refresh();
        navigate(`/workflow?execution=${execution.id}`);
      } else {
        navigate(`/projects/${project.id}`);
      }
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-2xl font-semibold tracking-tight">New project</h1>
      <p className="mt-1 text-sm text-slate-500">Describe what the client needs in plain language. The agent team will take it from there.</p>

      <ol className="my-6 grid grid-cols-4 gap-2" aria-label="Wizard steps">
        {STEPS.map((label, index) => (
          <li key={label} className="flex flex-col gap-2">
            <div className={cx("h-1.5 rounded-full", index <= step ? "bg-violet-600" : "bg-slate-200")} />
            <span className={cx("text-xs font-medium", index === step ? "text-violet-700" : "text-slate-400")}>
              {index + 1}. {label}
            </span>
          </li>
        ))}
      </ol>

      <Card className="p-6">
        {step === 0 && (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2 rounded-xl bg-violet-50 p-3 text-sm text-violet-800">
              <Sparkles size={16} /> Load a demo scenario:
              {Object.entries(EXAMPLES).map(([key, example]) => (
                <Button key={key} variant="secondary" size="sm" onClick={() => loadExample(key)}>{example.label}</Button>
              ))}
            </div>
            <Field label="Project name" required><input className={inputClass} value={form.name} onChange={set("name")} placeholder="e.g. Employee Leave Management System" /></Field>
            <Field label="Project description"><textarea rows={3} className={inputClass} value={form.description} onChange={set("description")} placeholder="Short summary of the project and the client" /></Field>
            <Field label="Business domain"><input className={inputClass} value={form.business_domain} onChange={set("business_domain")} placeholder="e.g. Human Resources, Retail, Healthcare" /></Field>
          </div>
        )}

        {step === 1 && (
          <div className="space-y-4">
            <Field label="Business requirement" required hint={`${form.requirement.length}/10000 characters. Write it the way the client would say it.`}>
              <textarea rows={8} maxLength={10000} className={inputClass} value={form.requirement} onChange={set("requirement")}
                placeholder="Build a web application that lets employees apply for leave, managers approve requests, and HR track balances…" />
            </Field>
            <Notice tone="info">The Requirement Analyst will extract functional and non-functional requirements, user stories and acceptance criteria, and will flag missing or ambiguous information rather than inventing it.</Notice>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4">
            <Field label="Preferred technology stack" hint="Optional. The Research agent will take this into account.">
              <input className={inputClass} value={form.preferred_tech_stack} onChange={set("preferred_tech_stack")} placeholder="e.g. Python FastAPI, React, PostgreSQL" />
            </Field>
            <Field label="Project complexity">
              <select className={inputClass} value={form.complexity} onChange={set("complexity")}>
                <option value="">Let the agents estimate</option><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option>
              </select>
            </Field>
            <Field label="Additional constraints" hint="One per line: budget, timeline, compliance, hosting…">
              <textarea rows={4} className={inputClass} value={form.constraints} onChange={set("constraints")} />
            </Field>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-5">
            <KeyValue items={[
              ["Project name", form.name],
              ["Business domain", form.business_domain || "—"],
              ["Complexity", form.complexity || "Agents will estimate"],
              ["Preferred stack", form.preferred_tech_stack || "—"],
            ]} />
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Requirement</p>
              <p className="mt-1 whitespace-pre-wrap rounded-xl bg-slate-50 p-3 text-sm text-slate-700">{form.requirement}</p>
            </div>
            <label className="flex items-start gap-3 rounded-xl border border-slate-200 p-4 cursor-pointer">
              <input type="checkbox" className="mt-1 accent-violet-600" checked={startNow} onChange={(e) => setStartNow(e.target.checked)} />
              <span>
                <span className="block text-sm font-medium text-slate-800">Start the AI workflow immediately</span>
                <span className="block text-xs text-slate-500">The workflow will pause for your approval after requirements, architecture, code, before tests run, and before final delivery.</span>
              </span>
            </label>
            {system?.llm_mode === "mock" && (
              <Notice tone="warning">No LLM API key is configured, so agents run in <b>mock mode</b> (rule-based outputs, clearly labelled). Set <code>LLM_API_KEY</code> in <code>backend/.env</code> for real LLM agents.</Notice>
            )}
          </div>
        )}

        <ErrorBanner error={error} className="mt-5" />

        <div className="mt-6 flex justify-between border-t border-slate-100 pt-5">
          <Button variant="secondary" icon={ArrowLeft} disabled={step === 0} onClick={() => setStep(step - 1)}>Back</Button>
          {step < STEPS.length - 1 ? (
            <Button disabled={!stepValid[step]} onClick={() => setStep(step + 1)}>Continue <ArrowRight size={15} /></Button>
          ) : (
            <Button icon={startNow ? Rocket : Check} loading={busy} onClick={submit}>{startNow ? "Create & start agents" : "Create project"}</Button>
          )}
        </div>
      </Card>
    </div>
  );
}
