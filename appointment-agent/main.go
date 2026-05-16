package main

import (
	"encoding/json"
	"log"
	"os"
	"os/signal"
	"syscall"

	"github.com/nats-io/nats.go"
)

const (
	subjectAppointment = "tasks.appointment"
	subjectCompleted   = "tasks.completed"
	queueGroup         = "appointment-agents"
)

type Agent struct {
	processor *AppointmentProcessor
	nc        *nats.Conn
}

func NewAgent(processor *AppointmentProcessor, nc *nats.Conn) *Agent {
	return &Agent{
		processor: processor,
		nc:        nc,
	}
}

func (a *Agent) Run() error {
	_, err := a.nc.QueueSubscribe(subjectAppointment, queueGroup, func(msg *nats.Msg) {
		var task Task
		if err := json.Unmarshal(msg.Data, &task); err != nil {
			a.publishResult(Result{
				TaskID:  "",
				Success: false,
				Output:  "invalid task format",
			})
			return
		}

		if task.Type != "appointment" {
			a.publishResult(Result{
				TaskID:  task.ID,
				Success: false,
				Output:  "unsupported task type",
			})
			return
		}

		var payload AppointmentPayload
		if err := json.Unmarshal(task.Payload, &payload); err != nil {
			a.publishResult(Result{
				TaskID:  task.ID,
				Success: false,
				Output:  "invalid payload format",
			})
			return
		}

		result := a.processor.Process(task.ID, payload)
		a.publishResult(result)
	})
	if err != nil {
		return err
	}

	log.Println("appointment agent started")
	return nil
}

func (a *Agent) publishResult(result Result) {
	data, err := json.Marshal(result)
	if err != nil {
		log.Printf("failed to marshal result: %v", err)
		return
	}

	if err := a.nc.Publish(subjectCompleted, data); err != nil {
		log.Printf("failed to publish result: %v", err)
	}
}

func main() {
	natsURL := os.Getenv("NATS_URL")
	if natsURL == "" {
		natsURL = nats.DefaultURL
	}

	nc, err := nats.Connect(natsURL)
	if err != nil {
		log.Fatalf("nats connect failed: %v", err)
	}
	defer nc.Close()

	validator := NewAppointmentValidator()
	store := NewInMemorySlotStore()
	processor := NewAppointmentProcessor(validator, store)
	agent := NewAgent(processor, nc)

	if err := agent.Run(); err != nil {
		log.Fatalf("agent run failed: %v", err)
	}

	sig := make(chan os.Signal, 1)
	signal.Notify(sig, syscall.SIGINT, syscall.SIGTERM)
	<-sig

	log.Println("appointment agent stopped")
}
