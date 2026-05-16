package main

import (
	"path/filepath"
	"testing"
	"time"
)

func TestAppointmentProcessorProcessSuccessOffline(t *testing.T) {
	t.Parallel()

	store := NewFileSlotStore(filepath.Join(t.TempDir(), "slots.json"))
	processor := NewAppointmentProcessor(NewAppointmentValidator(), store)
	preferredTime := time.Now().Add(2 * time.Hour)

	result := processor.Process("task-1", AppointmentPayload{
		FullName:          "Иванов Иван",
		BirthDate:         "1990-01-01",
		Contact:           "ivan@example.com",
		Specialty:         "Терапевт",
		PreferredDateTime: preferredTime,
		Type:              "offline",
	})

	if !result.Success {
		t.Fatalf("expected success, got failure: %v", result.Output)
	}

	output, ok := result.Output.(AppointmentOutput)
	if !ok {
		t.Fatalf("expected AppointmentOutput, got %T", result.Output)
	}

	if output.Location == "" {
		t.Fatal("expected non-empty location")
	}

	if output.DateTime.Format(time.RFC3339) != preferredTime.Format(time.RFC3339) {
		t.Fatalf("expected %s, got %s", preferredTime.Format(time.RFC3339), output.DateTime.Format(time.RFC3339))
	}
}

func TestAppointmentProcessorProcessRejectsPastDate(t *testing.T) {
	t.Parallel()

	store := NewFileSlotStore(filepath.Join(t.TempDir(), "slots.json"))
	processor := NewAppointmentProcessor(NewAppointmentValidator(), store)

	result := processor.Process("task-2", AppointmentPayload{
		FullName:          "Петров Петр",
		BirthDate:         "1990-01-01",
		Contact:           "petr@example.com",
		Specialty:         "Хирург",
		PreferredDateTime: time.Now().Add(-1 * time.Hour),
		Type:              "offline",
	})

	if result.Success {
		t.Fatal("expected failure for past date")
	}

	if result.Output != "preferred date time must be in the future" {
		t.Fatalf("unexpected error: %v", result.Output)
	}
}

func TestAppointmentProcessorProcessRejectsDuplicateSlot(t *testing.T) {
	t.Parallel()

	store := NewFileSlotStore(filepath.Join(t.TempDir(), "slots.json"))
	processor := NewAppointmentProcessor(NewAppointmentValidator(), store)
	preferredTime := time.Now().Add(3 * time.Hour)

	first := processor.Process("task-3", AppointmentPayload{
		FullName:          "Пациент А",
		BirthDate:         "1990-01-01",
		Contact:           "a@example.com",
		Specialty:         "Кардиолог",
		PreferredDateTime: preferredTime,
		Type:              "offline",
	})
	second := processor.Process("task-4", AppointmentPayload{
		FullName:          "Пациент Б",
		BirthDate:         "1991-01-01",
		Contact:           "b@example.com",
		Specialty:         "Кардиолог",
		PreferredDateTime: preferredTime,
		Type:              "offline",
	})

	if !first.Success {
		t.Fatalf("expected first booking to succeed, got %v", first.Output)
	}

	if second.Success {
		t.Fatal("expected duplicate slot to be rejected")
	}

	if second.Output != "slot is already booked" {
		t.Fatalf("unexpected error: %v", second.Output)
	}
}

func TestFileSlotStoreSharesStateAcrossInstances(t *testing.T) {
	t.Parallel()

	path := filepath.Join(t.TempDir(), "slots.json")
	storeA := NewFileSlotStore(path)
	storeB := NewFileSlotStore(path)
	preferredTime := time.Now().Add(4 * time.Hour)

	if !storeA.IsAvailable(preferredTime) {
		t.Fatal("expected slot to be available before booking")
	}

	if !storeA.Book(preferredTime) {
		t.Fatal("expected first booking to succeed")
	}

	if storeB.IsAvailable(preferredTime) {
		t.Fatal("expected second store instance to observe booked slot")
	}

	if storeB.Book(preferredTime) {
		t.Fatal("expected second booking to fail")
	}
}