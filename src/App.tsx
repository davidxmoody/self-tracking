import {
  CartesianGrid,
  Dot,
  Label,
  LabelList,
  Line,
  LineChart,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import oneRepMaxes from "./data/formatted/oneRepMaxes.json"
import programs from "./data/formatted/programs.json"

const exercises = {
  deadlift: "green",
  squat: "blue",
  bench: "red",
  overhead: "orange",
}

const yTickSize = 20
const maxHeight =
  yTickSize *
  Math.ceil(
    oneRepMaxes.reduce((max, {deadlift}) => Math.max(max, deadlift ?? 0), 0) /
      yTickSize,
  )

export default function App() {
  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        bottom: 0,
        left: 0,
        right: 0,
        padding: "70px 90px 60px 30px",
      }}
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={oneRepMaxes}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="date"
            ticks={programs.map((p) => p.start)}
            padding={{right: 140}}
          />
          <YAxis
            domain={[0, maxHeight]}
            tickCount={Math.floor(maxHeight / yTickSize) + 1}
          />

          {programs.map((program, i) => (
            <ReferenceArea
              x1={program.start}
              y1={0}
              x2={
                programs[i + 1]?.start ??
                oneRepMaxes[oneRepMaxes.length - 1].date
              }
              y2={maxHeight}
              stroke="none"
              fill="none"
            >
              <Label
                value={program.name}
                position="insideBottom"
                fontWeight="bold"
                offset={10}
              />
            </ReferenceArea>
          ))}

          {Object.entries(exercises).map(([exercise, color]) => (
            <Line
              key={exercise}
              dataKey={exercise}
              type="monotone"
              stroke={color}
              connectNulls
              dot={<Dot r={1} />}
            >
              <LabelList
                dataKey={exercise + "Last"}
                formatter={(value: number) => `${value}kg ${exercise}`}
                position="right"
                fontWeight="bold"
                offset={8}
              />
            </Line>
          ))}

          <Tooltip />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
