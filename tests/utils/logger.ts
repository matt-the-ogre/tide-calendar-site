/**
 * Logging utility for Playwright tests
 * Provides structured logging with timestamps and log levels
 */

export enum LogLevel {
  ERROR = 0,
  WARN = 1,
  INFO = 2,
  DEBUG = 3,
}

class Logger {
  private logLevel: LogLevel;
  private context: string;

  constructor(context: string = 'test', logLevel: LogLevel = LogLevel.INFO) {
    this.context = context;
    this.logLevel = logLevel;
  }

  private getTimestamp(): string {
    return new Date().toISOString();
  }

  private log(level: LogLevel, levelName: string, message: string, ...args: any[]): void {
    if (level <= this.logLevel) {
      const timestamp = this.getTimestamp();
      const formattedMessage = `[${timestamp}] [${levelName}] [${this.context}] ${message}`;

      switch (level) {
        case LogLevel.ERROR:
          console.error(formattedMessage, ...args);
          break;
        case LogLevel.WARN:
          console.warn(formattedMessage, ...args);
          break;
        case LogLevel.INFO:
          console.info(formattedMessage, ...args);
          break;
        case LogLevel.DEBUG:
          console.debug(formattedMessage, ...args);
          break;
      }
    }
  }

  error(message: string, ...args: any[]): void {
    this.log(LogLevel.ERROR, 'ERROR', message, ...args);
  }

  warn(message: string, ...args: any[]): void {
    this.log(LogLevel.WARN, 'WARN', message, ...args);
  }

  info(message: string, ...args: any[]): void {
    this.log(LogLevel.INFO, 'INFO', message, ...args);
  }

  debug(message: string, ...args: any[]): void {
    this.log(LogLevel.DEBUG, 'DEBUG', message, ...args);
  }
}

class LoggerFactory {
  private static instance: LoggerFactory;
  private loggers: Map<string, Logger> = new Map();
  private globalLogLevel: LogLevel = LogLevel.INFO;

  private constructor() {}

  static getInstance(): LoggerFactory {
    if (!LoggerFactory.instance) {
      LoggerFactory.instance = new LoggerFactory();
    }
    return LoggerFactory.instance;
  }

  setGlobalLogLevel(level: LogLevel): void {
    this.globalLogLevel = level;
  }

  getLogger(context: string): Logger {
    if (!this.loggers.has(context)) {
      this.loggers.set(context, new Logger(context, this.globalLogLevel));
    }
    return this.loggers.get(context)!;
  }
}

const factory = LoggerFactory.getInstance();

// Set log level from environment
const envLogLevel = process.env.LOG_LEVEL?.toUpperCase();
switch (envLogLevel) {
  case 'ERROR':
    factory.setGlobalLogLevel(LogLevel.ERROR);
    break;
  case 'WARN':
    factory.setGlobalLogLevel(LogLevel.WARN);
    break;
  case 'INFO':
    factory.setGlobalLogLevel(LogLevel.INFO);
    break;
  case 'DEBUG':
    factory.setGlobalLogLevel(LogLevel.DEBUG);
    break;
}

export default {
  getLogger: (context: string) => factory.getLogger(context),
  setLogLevel: (level: LogLevel) => factory.setGlobalLogLevel(level),
  LogLevel,
};