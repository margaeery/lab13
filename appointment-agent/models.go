package main

import (
	"encoding/json"
	"time"
)

type Task struct {
	ID      string          `json:"id"`
	Type    string          `json:"type"`
	Payload json.RawMessage `json:"payload"`
}

type Result struct {
	TaskID  string      `json:"task_id"`
	AgentID string      `json:"agent_id,omitempty"`
	Success bool        `json:"success"`
	Output  interface{} `json:"output"`
}

type AppointmentPayload struct {
	FullName          string    `json:"full_name"`
	BirthDate         string    `json:"birth_date"`
	Contact           string    `json:"contact"`
	Specialty         string    `json:"specialty"`
	PreferredDateTime time.Time `json:"preferred_date_time"`
	Type              string    `json:"type"`
}

type AppointmentOutput struct {
	DateTime time.Time `json:"date_time"`
	Location string    `json:"location"`
}
