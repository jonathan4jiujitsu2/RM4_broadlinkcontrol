CREATE TABLE sensor_data (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    board_num INT,
    channel INT,
    temperature FLOAT,
    power_w FLOAT,
    current_a FLOAT,
    voltage_v FLOAT,
    total_kwh FLOAT,
    ac_state VARCHAR(10),
    damper_state VARCHAR(10)
);

SELECT create_hypertable('sensor_data', 'timestamp');
