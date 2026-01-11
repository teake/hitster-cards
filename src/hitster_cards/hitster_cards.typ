#import "@preview/one-liner:0.2.0": fit-to-width 
#import "@preview/based:0.2.0": base64

#let songs = json(bytes(sys.inputs.songs))
#let edition = sys.inputs.at("edition", default: "")

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
  let qr_code = base64.decode(song.qr_code)
  let qr_size = 102% / calc.sqrt(2)
  let qr_image = image(qr_code, width: qr_size)
  let qr_padding_height = qr_size * 1/2 * (1 + calc.rem(song.qr_width, 2) / song.qr_width) 
  let qr_padding_image = box(clip: true, width: qr_size, height: qr_padding_height, image(qr_code, width: 100%))
  let qr_padding_shift = qr_size / 2 + qr_padding_height / 2
  square(
    size: card_size,
    inset: 0.65cm
  )[
    #place(center + horizon, circle(width: 105%))
    #place(center + horizon, circle(width: 100%))
    #box(clip: true, radius: 50%,
        width: 100%, height: 100%
    )[
        #place(center + horizon, dy: +qr_padding_shift, rotate(180deg, qr_padding_image))
        #place(center + horizon, dy: -qr_padding_shift, rotate(0deg, qr_padding_image))
        #place(center + horizon, dx: +qr_padding_shift, rotate(90deg, qr_padding_image))
        #place(center + horizon, dx: -qr_padding_shift, rotate(-90deg, qr_padding_image))
        #place(center + horizon, qr_image))
    ]
    #if edition != "" [
        #place(
            center + horizon,
            circle(
                width: 35%, 
                inset: 0pt, 
                fill: white,
                stroke: 1pt, 
                fit-to-width(text(weight: "black", upper(edition)))
            )
        )
    ]
  ]
}

#let text_back_side(song) = {
  square(
    size: card_size,
    inset: 0.1 * card_size,
    stack(
      // Artist
      block(
        height: 0.3 * card_size,
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
      // Year
      block(
        height: 0.2 * card_size,
        width: 100%,
        align(
          center + horizon,
          text(
            weight: "black",
            song.release_date.slice(0, 4),
            size: 0.28 * card_size
          )
        ),
      ),
      // Song Name
      block(
        height: 0.3 * card_size,
        width: 100%,
        align(
          center + horizon,
          text(
            {[_ #song.name _]},
            size: 0.06 * card_size
          )
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
