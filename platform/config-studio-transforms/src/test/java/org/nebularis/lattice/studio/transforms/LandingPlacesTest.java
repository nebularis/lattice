// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.transforms;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

import java.util.List;
import org.junit.jupiter.api.Test;
import org.nebularis.lattice.studio.transforms.LandingPlaces.Place;
import org.nebularis.lattice.studio.transforms.LandingPlaces.Values;

/** The exact assignment of a changed graph to a landing place (SVA-P3). A graph is a place's by equality, and never by a pattern or a prefix. */
class LandingPlacesTest {
    private static final Values VALUES = new Values("https://example.org/lending#borrower 1/é", "urn:rev:b/4", "2026-03");
    private static final Place DATA = new Place("p#data", "DataRole", null, "urn:g:borrower/{root}");
    private static final Place LOG = new Place("p#log", "LogRole", null, "urn:g:txlog/{month}");
    private static final Place ADD = new Place("p#add", "PatchRole", null, "{newRev}/add");
    private static final Place TXN = new Place("p#txn", "TxnRole", "urn:g:txn", null);
    private static final List<Place> PLACES = List.of(DATA, LOG, ADD, TXN);

    @Test
    void aRootIsPercentEncodedAsEncodeForUriDoesBeforeItIsCompared() {
        String encoded = "urn:g:borrower/https%3A%2F%2Fexample.org%2Flending%23borrower%201%2F%C3%A9";
        assertEquals(encoded, LandingPlaces.render("urn:g:borrower/{root}", VALUES));
        assertEquals(List.of(DATA), LandingPlaces.assign(PLACES, encoded, VALUES));
    }

    @Test
    void aGraphThatOnlyStartsLikeAPlaceOrHoldsTheRootUnencodedIsNoPlaces() {
        assertEquals(List.of(), LandingPlaces.assign(PLACES, "urn:g:borrower/https%3A%2F%2Fexample.org%2Flending%23borrower%201%2F%C3%A9/extra", VALUES));
        assertEquals(List.of(), LandingPlaces.assign(PLACES, "urn:g:borrower/https://example.org/lending#borrower 1/é", VALUES));
        assertEquals(List.of(), LandingPlaces.assign(PLACES, "urn:g:txlog/2026-04", VALUES), "another month is not this step's");
        assertEquals(List.of(), LandingPlaces.assign(PLACES, "urn:g:txlog/", VALUES));
        assertEquals(List.of(), LandingPlaces.assign(PLACES, "urn:g:txn/x", VALUES));
        assertEquals(List.of(), LandingPlaces.assign(PLACES, "urn:g:txn ", VALUES));
    }

    @Test
    void theMonthAndTheNewRevisionComeFromTheStep() {
        assertEquals(List.of(LOG), LandingPlaces.assign(PLACES, "urn:g:txlog/2026-03", VALUES));
        assertEquals(List.of(ADD), LandingPlaces.assign(PLACES, "urn:rev:b/4/add", VALUES));
        assertEquals(List.of(), LandingPlaces.assign(PLACES, "urn:rev:b/5/add", VALUES));
        assertEquals(List.of(TXN), LandingPlaces.assign(PLACES, "urn:g:txn", VALUES));
    }

    @Test
    void aTemplateWithAPlaceholderOutsideTheClosedSetOrOneTheStepDoesNotStateRendersAsNothing() {
        assertNull(LandingPlaces.render("urn:g:txlog/{year}", VALUES));
        assertNull(LandingPlaces.render("urn:g:txlog/{month", VALUES));
        assertNull(LandingPlaces.render("urn:g:borrower/{root}", new Values(null, null, "2026-03")));
        assertEquals(List.of(), LandingPlaces.assign(List.of(new Place("p#x", "LogRole", null, "urn:g:txlog/{year}")), "urn:g:txlog/{year}", VALUES));
    }

    @Test
    void twoPlacesThatRenderTheSameGraphAreBothReturnedInIriOrder() {
        Place a = new Place("p#a", "DataRole", "urn:g:same", null);
        Place b = new Place("p#b", "MetaRole", "urn:g:same", null);
        assertEquals(List.of(a, b), LandingPlaces.assign(List.of(b, a), "urn:g:same", VALUES));
    }
}
