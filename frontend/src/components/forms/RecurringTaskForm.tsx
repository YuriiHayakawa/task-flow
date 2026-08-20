import { Calendar, Check, Repeat, Type, X } from "lucide-react";
import { useState, type SubmitEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import type { RecurrenceType, RecurringTask } from "@/types/recurringTask";
import { getApiErrorMessage } from "@/utils/apiErrorMessage";

export interface RecurringTaskFormValues {
  title: string;
  recurrence_type: RecurrenceType;
  weekdays: number[];
  month_day: number | null;
}

const RECURRENCE_OPTIONS: { value: RecurrenceType; label: string }[] = [
  { value: "DAILY", label: "Diária" },
  { value: "WEEKLY", label: "Semanal" },
  { value: "MONTHLY", label: "Mensal" },
];

/** `value` segue `date.weekday()` do Python (0 = segunda ... 6 = domingo) —
 * mesma convenção do backend, sem tradução nenhuma nas duas pontas. */
const WEEKDAY_OPTIONS: { value: number; label: string }[] = [
  { value: 0, label: "Seg" },
  { value: 1, label: "Ter" },
  { value: 2, label: "Qua" },
  { value: 3, label: "Qui" },
  { value: 4, label: "Sex" },
  { value: 5, label: "Sáb" },
  { value: 6, label: "Dom" },
];

interface RecurringTaskFormProps {
  /** Presente em modo de edição; ausente em modo de criação. */
  recurringTask?: RecurringTask;
  onSubmit: (values: RecurringTaskFormValues) => Promise<void>;
  onCancel: () => void;
}

/** Mesmo padrão visual/estrutural de `TaskForm.tsx` (seletor de pílulas para
 * campo controlado) — os campos de dias da semana/dia do mês só aparecem
 * quando fazem sentido para o tipo de recorrência escolhido. */
export function RecurringTaskForm({ recurringTask, onSubmit, onCancel }: RecurringTaskFormProps) {
  const [title, setTitle] = useState(recurringTask?.title ?? "");
  const [recurrenceType, setRecurrenceType] = useState<RecurrenceType>(
    recurringTask?.recurrence_type ?? "DAILY",
  );
  const [weekdays, setWeekdays] = useState<number[]>(recurringTask?.weekdays ?? []);
  const [monthDay, setMonthDay] = useState<string>(recurringTask?.month_day?.toString() ?? "");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function toggleWeekday(day: number) {
    setWeekdays((current) =>
      current.includes(day)
        ? current.filter((selected) => selected !== day)
        : [...current, day].sort((a, b) => a - b),
    );
  }

  async function handleSubmit(event: SubmitEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await onSubmit({
        title,
        recurrence_type: recurrenceType,
        weekdays: recurrenceType === "WEEKLY" ? weekdays : [],
        month_day: recurrenceType === "MONTHLY" ? Number(monthDay) : null,
      });
    } catch (err) {
      setError(getApiErrorMessage(err, "Não foi possível salvar a tarefa fixa. Tente novamente."));
    } finally {
      setIsSubmitting(false);
    }
  }

  const canSubmit =
    title.trim() !== "" &&
    (recurrenceType !== "WEEKLY" || weekdays.length > 0) &&
    (recurrenceType !== "MONTHLY" ||
      (monthDay.trim() !== "" && Number(monthDay) >= 1 && Number(monthDay) <= 31));

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-5">
      <div className="flex flex-col gap-2">
        <Label htmlFor="recurring-task-title">Título</Label>
        <div className="relative">
          <Type className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            id="recurring-task-title"
            required
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            className="h-11 rounded-xl pl-9"
            placeholder="Ex.: Beber água"
          />
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <Label className="flex items-center gap-1.5">
          <Repeat className="size-3.5" />
          Repetição
        </Label>
        <div className="grid grid-cols-3 gap-2">
          {RECURRENCE_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => setRecurrenceType(option.value)}
              className={cn(
                "rounded-xl border px-2 py-2 text-xs font-medium transition-colors",
                recurrenceType === option.value
                  ? "border-blue-400 bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300"
                  : "border-border text-muted-foreground hover:bg-muted",
              )}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {recurrenceType === "WEEKLY" && (
        <div className="flex flex-col gap-2">
          <Label>Dias da semana</Label>
          <div className="grid grid-cols-7 gap-1.5">
            {WEEKDAY_OPTIONS.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => toggleWeekday(option.value)}
                className={cn(
                  "rounded-lg border px-1 py-2 text-xs font-medium transition-colors",
                  weekdays.includes(option.value)
                    ? "border-blue-400 bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300"
                    : "border-border text-muted-foreground hover:bg-muted",
                )}
              >
                {option.label}
              </button>
            ))}
          </div>
          {weekdays.length === 0 && (
            <p className="text-xs text-muted-foreground">Selecione ao menos um dia.</p>
          )}
        </div>
      )}

      {recurrenceType === "MONTHLY" && (
        <div className="flex flex-col gap-2">
          <Label htmlFor="recurring-task-month-day">Dia do mês</Label>
          <div className="relative">
            <Calendar className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              id="recurring-task-month-day"
              type="number"
              min={1}
              max={31}
              value={monthDay}
              onChange={(event) => setMonthDay(event.target.value)}
              className="h-11 rounded-xl pl-9"
              placeholder="Ex.: 10"
            />
          </div>
          <p className="text-xs text-muted-foreground">
            Em meses mais curtos que esse dia, cai no último dia do mês.
          </p>
        </div>
      )}

      {error && <p className="text-sm text-destructive">{error}</p>}

      <div className="mt-2 flex justify-end gap-2">
        <Button
          type="button"
          variant="outline"
          onClick={onCancel}
          disabled={isSubmitting}
          className="rounded-xl"
        >
          <X className="size-4" />
          Cancelar
        </Button>
        <Button
          type="submit"
          disabled={isSubmitting || !canSubmit}
          className="rounded-xl bg-blue-600 text-white hover:bg-blue-500"
        >
          <Check className="size-4" />
          {isSubmitting ? "Salvando..." : recurringTask ? "Salvar" : "Criar tarefa fixa"}
        </Button>
      </div>
    </form>
  );
}
