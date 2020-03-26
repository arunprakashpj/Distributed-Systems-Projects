/*
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package dspackage;

import org.apache.flink.api.common.functions.FilterFunction;
import org.apache.flink.api.common.functions.MapFunction;
import org.apache.flink.api.common.functions.ReduceFunction;
import org.apache.flink.api.java.tuple.Tuple3;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.datastream.SingleOutputStreamOperator;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.streaming.api.functions.timestamps.AscendingTimestampExtractor;
import org.apache.flink.streaming.api.windowing.assigners.TumblingEventTimeWindows;
import org.apache.flink.streaming.api.windowing.time.Time;

/**
 * Skeleton for a Flink Streaming Job.
 *
 * <p>For a tutorial how to write a Flink streaming application, check the
 * tutorials and examples on the <a href="https://flink.apache.org/docs/stable/">Flink Website</a>.
 *
 * <p>To package your application into a JAR file for execution, run
 * 'mvn clean package' on the command line.
 *
 * <p>If you change the name of the main class (with the public static void main(String[] args))
 * method, change the respective entry in the POM.xml file (simply search for 'mainClass').
 */
public class StreamingJob {

    public static void main(String[] args) throws Exception {
        final StreamExecutionEnvironment env =
                StreamExecutionEnvironment.getExecutionEnvironment();

        // Path to access the input file
        String path = "sample.txt";

        //Read the input text file from the path . After splitting rows using rowsplitter, use map over them followed by time stamp assignment
        DataStream<Tuple3<String, Integer, Integer>> carData = env.readTextFile(path).map(new RowSplitter()).assignTimestampsAndWatermarks(new CarTimestamp());

        //TumblingEventTimeWindows function is used for performing some operation in a particular time window .
        //In a particular time window of 1 minute , A1: the average speed (computed over a tumbling window of 1 minute) of cars traveling faster than 20 MPH and
        // A2: the average speed (computed over a tumbling window of 1 minute) of cars traveling slower than 20 MPH are calculated. An alert is generated each time the
        // value |A2-A1| for the same event time is greater than 20 MPH ´by filtering out the average speeds over 20 MPH
        DataStream<Tuple3<String, Integer, Integer>> result = carData.windowAll(TumblingEventTimeWindows.of(Time.seconds(60))).reduce(new average()).filter(new Filter());

		result.print();
		//The output file  alert.text containing the results are created in this location. It contains the alert data  generated whenever |A2-A1| for the particular event time is
        // greater than 20 MPH
		result.writeAsText("/media/sf_UDrive/alert");

        env.execute("Data Streaming");
    }


    public static class RowSplitter implements
            MapFunction<String, Tuple3<String, Integer, Integer>> {

        public Tuple3<String, Integer, Integer> map(String row)
                throws Exception {
            // The row are split
            String[] fields = row.split(",");
            // 1st, 2nd and 3th field of csv are time, Vehicle ID,Speed respectively. They are the only required fields here.
            // Keeping the first field as Vehicle ID(String)
            // time as second field(Number) and speed as third field(Number)
            return new Tuple3<String, Integer, Integer>(
                    fields[2], Integer.valueOf(fields[1]), Integer.valueOf(fields[3]));
        }

    }


    private static class CarTimestamp extends AscendingTimestampExtractor<Tuple3<String, Integer, Integer>> {
        private static final long serialVersionUID = 1L;

        @Override
        public long extractAscendingTimestamp(Tuple3<String, Integer, Integer> element) {
            return element.f1 * 1000;
        }
    }

   //The major computation is performed here. The |A2-A1| is calculated here after getting average speeds of vehicles travelling over 20 MPH and below 20 MPH
    public static class average implements
            ReduceFunction<Tuple3<String, Integer, Integer>> {
        int maxTotal = 0,minTotal = 0,minAvg = 0,maxCount = 0,minCount = 0,maxAvg = 0,total = 0;

        @Override
        public Tuple3<String, Integer, Integer> reduce(Tuple3<String, Integer, Integer> cumulative, Tuple3<String, Integer, Integer> input) throws Exception {
             //input.f2 is the speed of the particular vehicle
             // Checking whether  it is greater than 20 MPH
            if (input.f2 > 20) {
                // sum the speeds if the speed is above 20 MPH in the particular window
                maxTotal = maxTotal + input.f2;
                //maxCount is incremented to know the number of vehicles involved in the computation
                maxCount++;
                //Average is calculated
                maxAvg = maxTotal / maxCount;
            }
            //input.f2 is the speed of the particular vehicle
            // Checking whether  it is lesser than 20 MPH
            if (input.f2 < 20) {
                // sum the speeds if the speed is below 20 MPH in the particular window
                minTotal = minTotal + input.f2;
                //minCount is incremented to know the number of vehicles involved in the computation
                minCount++;
                //Average is calculated
                minAvg = minTotal / minCount;
            }
           // The |A2-A1| is calculated
            total = Math.abs(minAvg - maxAvg);

            // Tuple containing vehicle ID , time and average speed are returned
            return new Tuple3<String, Integer, Integer>(input.f0, input.f1, total);
        }
    }

    //Alert message is generated only when the calculated |A2-A1| is greater than 20 MPH
    public static class Filter implements FilterFunction<Tuple3<String, Integer, Integer>> {

        @Override
        public boolean filter(Tuple3<String, Integer, Integer> input) throws Exception {
            try {
                //filtering the tuple with average speed greater than 20 MPH
                if (input.f2 > 20)
                    return true;
            } catch (Exception ex) {
                System.out.print("Error in filter function");
            }
            return false;
        }
    }
}


