import {addDays, format, parseISO} from "date-fns"

export default function dateRange(
  startInclusive: string,
  endExclusive: string,
) {
  const range: string[] = []

  let currentDate = startInclusive

  while (currentDate < endExclusive) {
    range.push(currentDate)
    currentDate = format(addDays(parseISO(currentDate), 1), "yyyy-MM-dd")
  }

  return range
}
