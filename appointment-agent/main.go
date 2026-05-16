package main

import (
	"encoding/json"
	"log"
	"os"
	"os/signal"
	"sync/atomic"
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
	logger    *Logger
	id        string
	tasks     atomic.Int64
}

func NewAgent(processor *AppointmentProcessor, nc *nats.Conn, logger *Logger, id string) *Agent {
	return &Agent{
		processor: processor,
		nc:        nc,
		logger:    logger,
		id:        id,
	}
}

func (a *Agent) Run() error {
	_, err := a.nc.QueueSubscribe(subjectAppointment, queueGroup, func(msg *nats.Msg) {
		a.tasks.Add(1)

		var task Task
		if err := json.Unmarshal(msg.Data, &task); err != nil {
			a.logger.Error("unmarshal task failed: %v", err)
			a.publishResult(Result{
				TaskID:  "",
				AgentID: a.id,
				Success: false,
				Output:  "invalid task format",
			})
			return
		}

		if task.Type != "appointment" {
			a.logger.Error("unsupported task type: %s", task.Type)
			a.publishResult(Result{
				TaskID:  task.ID,
				AgentID: a.id,
				Success: false,
				Output:  "unsupported task type",
			})
			return
		}

		var payload AppointmentPayload
		if err := json.Unmarshal(task.Payload, &payload); err != nil {
			a.logger.Error("unmarshal payload failed: %v", err)
			a.publishResult(Result{
				TaskID:  task.ID,
				AgentID: a.id,
				Success: false,
				Output:  "invalid payload format",
			})
			return
		}

		a.logger.Info("processing task_id=%s agent_id=%s", task.ID, a.id)
		result := a.processor.Process(task.ID, payload)
		result.AgentID = a.id
		a.logger.Info("task done task_id=%s success=%v agent_id=%s processed=%d", task.ID, result.Success, a.id, a.tasks.Load())
		a.publishResult(result)
	})
	if err != nil {
		return err
	}

	a.logger.Info("agent started, id=%s listening on %s", a.id, subjectAppointment)
	return nil
}

func (a *Agent) publishResult(result Result) {
	data, err := json.Marshal(result)
	if err != nil {
		a.logger.Error("marshal result failed: %v", err)
		return
	}

	if err := a.nc.Publish(subjectCompleted, data); err != nil {
		a.logger.Error("publish result failed: %v", err)
	}
}

func main() {
	logger := NewLogger("agent")

	natsURL := os.Getenv("NATS_URL")
	if natsURL == "" {
		natsURL = nats.DefaultURL
	}

	logger.Info("connecting to NATS at %s", natsURL)
	nc, err := nats.Connect(natsURL)
	if err != nil {
		log.Fatalf("nats connect failed: %v", err)
	}
	defer nc.Close()

	validator := NewAppointmentValidator()
	store := NewFileSlotStore(os.Getenv("SLOT_STORE_PATH"))
	processor := NewAppointmentProcessor(validator, store)
	agentID := os.Getenv("AGENT_ID")
	if agentID == "" {
		hostname, err := os.Hostname()
		if err == nil && hostname != "" {
			agentID = hostname
		} else {
			agentID = "agent"
		}
	}

	agent := NewAgent(processor, nc, logger, agentID)

	if err := agent.Run(); err != nil {
		log.Fatalf("agent run failed: %v", err)
	}

	sig := make(chan os.Signal, 1)
	signal.Notify(sig, syscall.SIGINT, syscall.SIGTERM)
	<-sig

	logger.Info("agent stopped, total processed: %d", agent.tasks.Load())
}