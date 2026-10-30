#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <sys/un.h>
#include <unistd.h>

#define MAX_PAYLOAD (1024 * 1024)
#define HEADER_SIZE 256
#define IO_TIMEOUT_MS 1000

static const char *argument_value(int argc, char **argv, const char *name) {
    int index;
    for (index = 1; index + 1 < argc; index++) {
        if (strcmp(argv[index], name) == 0) {
            return argv[index + 1];
        }
    }
    return NULL;
}

static int write_all(int descriptor, const void *buffer, size_t length) {
    const unsigned char *cursor = (const unsigned char *)buffer;
    while (length > 0) {
        ssize_t written = write(descriptor, cursor, length);
        if (written < 0) {
            if (errno == EINTR) {
                continue;
            }
            return -1;
        }
        cursor += written;
        length -= (size_t)written;
    }
    return 0;
}

static int connect_with_timeout(
    int descriptor,
    const struct sockaddr *address,
    socklen_t address_length
) {
    int flags = fcntl(descriptor, F_GETFL, 0);
    int socket_error = 0;
    socklen_t socket_error_length = sizeof(socket_error);
    struct pollfd writable;

    if (flags < 0 || fcntl(descriptor, F_SETFL, flags | O_NONBLOCK) < 0) {
        return -1;
    }
    if (connect(descriptor, address, address_length) < 0 && errno != EINPROGRESS) {
        return -1;
    }

    writable.fd = descriptor;
    writable.events = POLLOUT;
    writable.revents = 0;
    while (poll(&writable, 1, IO_TIMEOUT_MS) < 0) {
        if (errno != EINTR) {
            return -1;
        }
    }
    if (!(writable.revents & POLLOUT) ||
        getsockopt(
            descriptor,
            SOL_SOCKET,
            SO_ERROR,
            &socket_error,
            &socket_error_length
        ) < 0 ||
        socket_error != 0) {
        return -1;
    }
    return fcntl(descriptor, F_SETFL, flags);
}

int main(int argc, char **argv) {
    const char *agent = argument_value(argc, argv, "--agent");
    const char *event = argument_value(argc, argv, "--event");
    const char *socket_path = argument_value(argc, argv, "--socket");
    unsigned char *payload = NULL;
    size_t used = 0;
    int descriptor = -1;
    int result = 1;
    char header[HEADER_SIZE];
    struct sockaddr_un address;
    struct timeval write_timeout;

    if (!agent || !event || !socket_path ||
        strlen(agent) > 64 || strlen(event) > 96 ||
        strlen(socket_path) >= sizeof(address.sun_path) ||
        strchr(agent, '"') || strchr(event, '"')) {
        return 2;
    }

    payload = (unsigned char *)malloc(MAX_PAYLOAD + 1);
    if (!payload) {
        return 3;
    }
    while (used <= MAX_PAYLOAD) {
        ssize_t count = read(STDIN_FILENO, payload + used, MAX_PAYLOAD + 1 - used);
        if (count == 0) {
            break;
        }
        if (count < 0) {
            if (errno == EINTR) {
                continue;
            }
            goto cleanup;
        }
        used += (size_t)count;
    }
    if (used == 0 || used > MAX_PAYLOAD) {
        goto cleanup;
    }

    memset(&address, 0, sizeof(address));
    address.sun_family = AF_UNIX;
    memcpy(address.sun_path, socket_path, strlen(socket_path) + 1);
    descriptor = socket(AF_UNIX, SOCK_STREAM, 0);
    if (descriptor < 0) {
        goto cleanup;
    }
    write_timeout.tv_sec = IO_TIMEOUT_MS / 1000;
    write_timeout.tv_usec = (IO_TIMEOUT_MS % 1000) * 1000;
    if (setsockopt(
            descriptor,
            SOL_SOCKET,
            SO_SNDTIMEO,
            &write_timeout,
            sizeof(write_timeout)
        ) < 0 || connect_with_timeout(
            descriptor,
            (struct sockaddr *)&address,
            sizeof(address)
        ) < 0) {
        goto cleanup;
    }

    signal(SIGPIPE, SIG_IGN);

    {
        int header_length = snprintf(
            header,
            sizeof(header),
            "{\"agent\":\"%s\",\"event\":\"%s\"}\n",
            agent,
            event
        );
        if (header_length <= 0 || (size_t)header_length >= sizeof(header)) {
            goto cleanup;
        }
        if (write_all(descriptor, header, (size_t)header_length) < 0 ||
            write_all(descriptor, payload, used) < 0) {
            goto cleanup;
        }
    }
    result = 0;

cleanup:
    if (descriptor >= 0) {
        close(descriptor);
    }
    free(payload);
    return result;
}
