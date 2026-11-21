package main

import (
	"fmt"
	"net"
	"sync"
	"time"

	pb "paper/pb"

	"google.golang.org/protobuf/proto"
)

const (
	listenAddr  = ":9193"
	gameTTL     = 3 * time.Second
	sweepPeriod = 500 * time.Millisecond
)

type gameEntry struct {
	GameName string
	Config   *pb.GameConfig
	CanJoin  bool
	Players  int32
	Master   *net.UDPAddr
	LastSeen time.Time
}

type catalog struct {
	mu    sync.Mutex
	games map[string]*gameEntry
}

func newCatalog() *catalog { return &catalog{games: make(map[string]*gameEntry)} }

func key(g, m string) string { return g + "|" + m }

func (c *catalog) onAnnouncement(addr *net.UDPAddr, ann *pb.AnnouncementMsg) {
	c.mu.Lock()
	defer c.mu.Unlock()
	for _, g := range ann.Games {
		c.games[key(g.GameName, addr.String())] = &gameEntry{
			GameName: g.GameName,
			Config:   g.Config,
			CanJoin:  g.CanJoin,
			Players:  g.PlayersCount,
			Master:   addr,
			LastSeen: time.Now(),
		}
	}
}

func (c *catalog) buildAnnouncement() *pb.AnnouncementMsg {
	c.mu.Lock()
	defer c.mu.Unlock()
	now := time.Now()
	out := &pb.AnnouncementMsg{}
	for k, g := range c.games {
		if now.Sub(g.LastSeen) > gameTTL {
			delete(c.games, k)
			continue
		}
		out.Games = append(out.Games, &pb.GameAnnouncement{
			GameName:     g.GameName + "|" + g.Master.String(),
			Config:       g.Config,
			CanJoin:      g.CanJoin,
			PlayersCount: g.Players,
		})
	}
	return out
}

func (c *catalog) sweep() {
	c.mu.Lock()
	defer c.mu.Unlock()
	now := time.Now()
	for k, g := range c.games {
		if now.Sub(g.LastSeen) > gameTTL {
			delete(c.games, k)
		}
	}
}

func main() {
	addr, err := net.ResolveUDPAddr("udp4", listenAddr)
	if err != nil {
		panic(err)
	}
	conn, err := net.ListenUDP("udp4", addr)
	if err != nil {
		panic(err)
	}
	defer conn.Close()

	cat := newCatalog()
	var seq int64

	go func() {
		t := time.NewTicker(sweepPeriod)
		for range t.C {
			cat.sweep()
		}
	}()

	buf := make([]byte, 2048)
	for {
		n, from, err := conn.ReadFromUDP(buf)
		if err != nil {
			continue
		}
		var msg pb.GameMessage
		if err := proto.Unmarshal(buf[:n], &msg); err != nil {
			continue
		}
		if msg.ProtocolVersion != 2 {
			continue
		}

		switch p := msg.Payload.(type) {
		case *pb.GameMessage_Announcement:
			cat.onAnnouncement(from, p.Announcement)
		case *pb.GameMessage_Discover:
			ann := cat.buildAnnouncement()
			if len(ann.Games) == 0 {
				continue
			}
			seq++
			out := &pb.GameMessage{
				ProtocolVersion: 2,
				MsgSeq:          seq,
				Payload:         &pb.GameMessage_Announcement{Announcement: ann},
			}
			b, err := proto.Marshal(out)
			if err == nil && len(b) <= 65000 {
				conn.WriteToUDP(b, from)
			}
			fmt.Printf("discover from %s -> %d games\n", from, len(ann.Games))
		}
	}
}
