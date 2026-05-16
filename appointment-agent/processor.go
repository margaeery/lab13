package main

import (
	"fmt"
	"strings"
)

type AppointmentProcessor struct {
	validator Validator
	store     SlotStore
}

func NewAppointmentProcessor(validator Validator, store SlotStore) *AppointmentProcessor {
	return &AppointmentProcessor{
		validator: validator,
		store:     store,
	}
}

func (p *AppointmentProcessor) Process(taskID string, payload AppointmentPayload) Result {
	if err := p.validator.Validate(payload); err != nil {
		return Result{
			TaskID:  taskID,
			Success: false,
			Output:  err.Error(),
		}
	}

	if !p.store.IsAvailable(payload.PreferredDateTime) {
		return Result{
			TaskID:  taskID,
			Success: false,
			Output:  "slot is already booked",
		}
	}

	if !p.store.Book(payload.PreferredDateTime) {
		return Result{
			TaskID:  taskID,
			Success: false,
			Output:  "slot is already booked",
		}
	}

	location := p.resolveLocation(payload)

	return Result{
		TaskID:  taskID,
		Success: true,
		Output: AppointmentOutput{
			DateTime: payload.PreferredDateTime,
			Location: location,
		},
	}
}

func (p *AppointmentProcessor) resolveLocation(payload AppointmentPayload) string {
	if payload.Type == "online" {
		return "https://telemedicine.example.com/room/" + payload.Contact
	}
	return fmt.Sprintf("Cabinet %d", hashSpecialty(payload.Specialty)%50+1)
}

func hashSpecialty(s string) int {
	s = strings.ToLower(strings.TrimSpace(s))
	h := 0
	for _, c := range s {
		h = 31*h + int(c)
	}
	if h < 0 {
		h = -h
	}
	return h
}
