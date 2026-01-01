#let songs = json(bytes(sys.inputs.songs))

// edition if defined, otherwise empty
#let edition = sys.inputs.at("edition", default:"")

// this is DIN A4
#let page_width = 210mm
#let page_height = 297mm

#let margin_x = 2cm
#let margin_y = 1cm

#let rows = 5
#let cols = 3
#let card_size = 5cm

#let marking_padding = 1cm

#assert(rows * card_size + 2 * marking_padding + margin_y <= page_height)
#assert(cols * card_size + 2 * marking_padding + margin_x <= page_width)

#set page(
  width: page_width,
  height: page_height,
  margin: (
    x: margin_x,
    y: margin_y
  )
)

// set font
#set text(font: (
  sys.inputs.at("font", default: "New Computer Modern"), // use input font or default
  "New Computer Modern" // fallback if input font is invalid
))

#set square(
  stroke: none
)

#let qr_front_side(song) = {
  square(
    size: card_size,
    inset: 0.5cm,
    image(
      bytes(song.svg),
      width: 100%
    )
  )
}

/// Renders string `s` scaled to fit within `target_width`, with optional text options.
/// Shows the scaled text, with a maximum font size of 28% of card size.
#let fit_text_to_width(s, target_width, ..opts) = {
  context {
    let base = 10pt
    let probe = text(size: base, ..opts)[#s]
    let w = measure(probe).width
    let ratio = if w == 0pt { 1 } else { target_width / w }
    let fs = calc.min(base * ratio, 0.28 * card_size)
    text(size: fs, ..opts)[#s]
    //linebreak()
    //text(size: 6pt)[#fs]
  }
}

#let text_back_side(song) = {
  square(
    size: card_size,
    inset: 0.05 * card_size,
    stack(
      // Artist
      block(
        height: 0.25 * card_size,
        width: 100%,
        align(
          center + horizon,
          text(
            //for no-wrap of artist names
            song.artists.map(artist => box(artist)).join([, ]),
            size: 0.06 * card_size
          )
        ),
      ),
      // Day and Month
      block(
        height: 0.1 * card_size,
        width: 100%,
        align(
          center + horizon,
          text(
            [#song.day #song.month],
            size: 0.06 * card_size
          )
        ),
      ),
      // Year
      block(
        height: 0.2 * card_size,
        width: 100%,
        align(
          center + horizon,
          fit_text_to_width(song.year, 0.85 * card_size, weight: "black")
        ),
      ),
      // Song Name
      block(
        height: 0.35 * card_size,
        width: 100%,
        align(
          center + horizon,
          text(
            if ("custom" in song) and song.custom == "true" {[ #song.name ]} else {[_ #song.name _]},
            size: 0.06 * card_size
          )
        )
      ),
      // Edition on bottom right corner (if defined)
      align(
        right + bottom,
        text(
          [ #edition ],
          size: 0.04 * card_size,
          fill: luma(35%)
        )
      )
    )
  )
}

#let marking_line = line(
  stroke: (
    paint: gray,
    thickness: 0.5pt
  ),
  length: marking_padding * 0.8  // 13.5cm for full lines
)

//a rotatable box with cut markings
#let marking(angle) = {
  rotate(
    angle,
    reflow: true,
    box(
      width: marking_padding,
      height: card_size,
      stack(
        spacing: card_size,
        ..(marking_line,) * 2
      )
    )
  )
}

//a row of markings
#let marking_row(angle) = {
  (
    square(
      size: marking_padding,
    ),
    ..(marking(angle),) * cols,
    square(
      size: marking_padding,
    ),
  )
}

#let pad_page(page) = {
  let rows = page.chunks(cols)

  //pad left and right
  let padded_rows = rows.map(
    row => (
      marking(0deg),
      row,
      marking(180deg)
    )
  )

  //pad top and bottom
  return (
    ..marking_row(90deg),
    ..padded_rows.flatten(),
    ..marking_row(270deg)
  )
}


#let get_pages(songs) = {
  let pages = ()

  //add test and qr codes
  for page in songs.chunks(rows*cols) {
    let fronts = ()
    let backs = ()

    for song in page {
      fronts.push(qr_front_side(song))
      backs.push(text_back_side(song))
    }

    //fill remaining slots with empty boxes if needed
    for _ in range(rows * cols - page.len()) {
      fronts.push(
        square(
          size: card_size
        )
      )
      backs.push(
        square(
          size: card_size
        )
      )
    }

    //reverse back side
    let back_rows = backs.chunks(cols)
    let reversed_back_rows = back_rows.map(row => row.rev())
    let reversed_backs = reversed_back_rows.flatten()

    pages.push(pad_page(fronts))
    pages.push(pad_page(reversed_backs))
  }
  return pages
}

#for (i, page) in get_pages(songs).enumerate() {
  if i != 0 {
    pagebreak()
  }
  grid(
    columns: cols + 2,
    ..page
  )
}
