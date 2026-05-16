package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"time"
)

type SlotStore interface {
	IsAvailable(t time.Time) bool
	Book(t time.Time) bool
}

type FileSlotStore struct {
	path     string
	lockPath string
}

func NewFileSlotStore(path string) *FileSlotStore {
	if path == "" {
		path = filepath.Join("data", "slots.json")
	}

	return &FileSlotStore{
		path:     path,
		lockPath: path + ".lock",
	}
}

func (s *FileSlotStore) IsAvailable(t time.Time) bool {
	slots, unlock, err := s.loadSlots()
	if err != nil {
		return false
	}
	defer unlock()

	return !slots[t.Format(time.RFC3339)]
}

func (s *FileSlotStore) Book(t time.Time) bool {
	slots, unlock, err := s.loadSlots()
	if err != nil {
		return false
	}
	defer unlock()

	key := t.Format(time.RFC3339)
	if slots[key] {
		return false
	}

	slots[key] = true
	if err := s.saveSlots(slots); err != nil {
		return false
	}

	return true
}

func (s *FileSlotStore) loadSlots() (map[string]bool, func(), error) {
	unlock, err := s.acquireLock()
	if err != nil {
		return nil, nil, err
	}

	if err := os.MkdirAll(filepath.Dir(s.path), 0755); err != nil {
		unlock()
		return nil, nil, err
	}

	data, err := os.ReadFile(s.path)
	if err != nil {
		if os.IsNotExist(err) {
			return map[string]bool{}, unlock, nil
		}
		unlock()
		return nil, nil, err
	}

	if len(data) == 0 {
		return map[string]bool{}, unlock, nil
	}

	slots := make(map[string]bool)
	if err := json.Unmarshal(data, &slots); err != nil {
		unlock()
		return nil, nil, err
	}

	return slots, unlock, nil
}

func (s *FileSlotStore) saveSlots(slots map[string]bool) error {
	data, err := json.Marshal(slots)
	if err != nil {
		return err
	}

	return os.WriteFile(s.path, data, 0644)
}

func (s *FileSlotStore) acquireLock() (func(), error) {
	if err := os.MkdirAll(filepath.Dir(s.lockPath), 0755); err != nil {
		return nil, err
	}

	deadline := time.Now().Add(5 * time.Second)
	for {
		lockFile, err := os.OpenFile(s.lockPath, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0644)
		if err == nil {
			return func() {
				lockFile.Close()
				os.Remove(s.lockPath)
			}, nil
		}

		if !os.IsExist(err) {
			return nil, err
		}

		if time.Now().After(deadline) {
			return nil, err
		}

		time.Sleep(10 * time.Millisecond)
	}
}
