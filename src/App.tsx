import {
  CartesianGrid,
  Dot,
  Label,
  LabelList,
  Line,
  LineChart,
  ReferenceArea,
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
    <div style={{marginTop: 100}}>
      <LineChart
        width={1200}
        height={500}
        data={oneRepMaxes}
        margin={{top: 5, right: 130, left: 20, bottom: 5}}
      >
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis
          dataKey="date"
          ticks={programs.map((p) => p.start)}
          padding={{right: 120}}
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
              programs[i + 1]?.start ?? oneRepMaxes[oneRepMaxes.length - 1].date
            }
            y2={maxHeight}
            stroke="red"
            strokeOpacity={0.3}
          >
            <Label value={program.name} position="insideBottom" />
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
            />
          </Line>
        ))}

        <Tooltip />
      </LineChart>
    </div>
  )
}
