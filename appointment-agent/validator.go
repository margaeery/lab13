package main

import (
	"errors"
	"time"
)

type Validator interface {
	Validate(payload AppointmentPayload) error
}

type AppointmentValidator struct{}

func NewAppointmentValidator() *AppointmentValidator {
	return &AppointmentValidator{}
}

func (v *AppointmentValidator) Validate(payload AppointmentPayload) error {
	if payload.FullName == "" {
		return errors.New("full name is required")
	}
	if payload.BirthDate == "" {
		return errors.New("birth date is required")
	}
	if payload.Contact == "" {
		return errors.New("contact is required")
	}
	if payload.Specialty == "" {
		return errors.New("specialty is required")
	}
	if payload.PreferredDateTime.IsZero() {
		return errors.New("preferred date time is required")
	}
	if payload.PreferredDateTime.Before(time.Now()) {
		return errors.New("preferred date time must be in the future")
	}
	if payload.Type != "offline" && payload.Type != "online" {
		return errors.New("type must be offline or online")
	}
	return nil
}
