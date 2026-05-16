package main

import (
	"sync"
	"time"
)

type SlotStore interface {
	IsAvailable(t time.Time) bool
	Book(t time.Time) bool
}

type InMemorySlotStore struct {
	mu    sync.Mutex
	slots map[string]bool
}

func NewInMemorySlotStore() *InMemorySlotStore {
	return &InMemorySlotStore{
		slots: make(map[string]bool),
	}
}

func (s *InMemorySlotStore) IsAvailable(t time.Time) bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	return !s.slots[t.Format(time.RFC3339)]
}

func (s *InMemorySlotStore) Book(t time.Time) bool {
	s.mu.Lock()
	defer s.mu.Unlock()

	key := t.Format(time.RFC3339)
	if s.slots[key] {
		return false
	}

	s.slots[key] = true
	return true
}
