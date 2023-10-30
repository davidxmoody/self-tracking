const records: Array<{
  type: string
  date: string
  value: number
}> = require("./output.json")

const data: Record<
  string,
  {weight: number; eaten: number; burned: number; base: number}
> = {}

for (const {type, date, value} of records) {
  switch (type) {
    case "bodyMassLb":
      data[date] = {...data[date], weight: value}
      break
    case "eatenCalories":
      data[date] = {...data[date], eaten: value}
      break
    case "energyBurnedActive":
      data[date] = {...data[date], burned: (data[date]?.burned ?? 0) + value}
      break
    case "energyBurnedBase":
      data[date] = {...data[date], base: (data[date]?.base ?? 0) + value}
      break
  }
}

const entries = Object.entries(data)
  .filter(([date]) => date >= "2020-04-08")
  .sort(([dateA], [dateB]) => (dateA < dateB ? -1 : 1))

console.log("date	eaten	burned	base	weight")

for (const [date, {weight, eaten, burned, base}] of entries) {
  console.log(
    `${date}	${eaten}	${Math.round(burned)}	${Math.round(base)}	${weight ?? ""}`,
  )
}
