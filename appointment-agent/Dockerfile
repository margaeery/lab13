FROM golang:1.25-alpine AS build
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o /bin/appointment-agent .

FROM alpine:3.20
WORKDIR /app
RUN apk add --no-cache su-exec
RUN adduser -D appuser && mkdir -p /app/data && chown -R appuser:appuser /app
COPY --from=build /bin/appointment-agent /usr/local/bin/appointment-agent
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
