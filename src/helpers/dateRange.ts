import {addDays, format, parseISO} from "date-fns"

export default function dateRange(
  startInclusive: string,
  endInclusive: string,
) {
  const range: string[] = []

  let currentDate = startInclusive

  while (currentDate <= endInclusive) {
    range.push(currentDate)
    currentDate = format(addDays(parseISO(currentDate), 1), "yyyy-MM-dd")
  }

  return range
}
