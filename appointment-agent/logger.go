package main

import (
	"fmt"
	"io"
	"log"
	"os"
	"path/filepath"
	"runtime"
	"time"
)

type LogLevel int

const (
	LevelDebug LogLevel = iota
	LevelInfo
	LevelError
)

type Logger struct {
	name       string
	fileHandle *os.File
	console    *log.Logger
	file       *log.Logger
}

func NewLogger(name string) *Logger {
	logsDir := "logs"
	os.MkdirAll(logsDir, 0755)

	filePath := filepath.Join(logsDir, name+".log")
	fh, err := os.OpenFile(filePath, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0644)
	if err != nil {
		log.Fatalf("failed to open log file: %v", err)
	}

	consoleFlags := log.Lmsgprefix
	fileFlags := log.LstdFlags

	return &Logger{
		name:       name,
		fileHandle: fh,
		console:    log.New(os.Stdout, "", consoleFlags),
		file:       log.New(io.MultiWriter(fh), "", fileFlags),
	}
}

func (l *Logger) format(level string, format string, args ...interface{}) string {
	msg := fmt.Sprintf(format, args...)
	_, file, line, _ := runtime.Caller(2)
	short := filepath.Base(file)
	return fmt.Sprintf("[%s] %-5s %s:%d | %s", time.Now().Format("15:04:05"), level, short, line, msg)
}

func (l *Logger) Info(format string, args ...interface{}) {
	l.console.Println(l.format("INFO", format, args...))
	l.file.Println(l.format("INFO", format, args...))
}

func (l *Logger) Error(format string, args ...interface{}) {
	l.console.Println(l.format("ERROR", format, args...))
	l.file.Println(l.format("ERROR", format, args...))
}

func (l *Logger) Debug(format string, args ...interface{}) {
	msg := l.format("DEBUG", format, args...)
	l.file.Println(msg)
}

func (l *Logger) Close() {
	if l.fileHandle != nil {
		l.fileHandle.Close()
	}
}
